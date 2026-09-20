#include <torch/extension.h>
#include <ATen/Parallel.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <mutex>
#include <vector>

namespace {
constexpr int64_t kGroup = 5;
constexpr int64_t kPatterns = 243;

const std::array<std::array<int8_t, kGroup>, kPatterns>& pattern_trits() {
  static std::array<std::array<int8_t, kGroup>, kPatterns> values{};
  static std::once_flag initialized;
  std::call_once(initialized, []() {
    for (int64_t pattern = 0; pattern < kPatterns; ++pattern) {
      int64_t value = pattern;
      for (int64_t k = 0; k < kGroup; ++k) {
        values[pattern][k] = static_cast<int8_t>(value % 3 - 1);
        value /= 3;
      }
    }
  });
  return values;
}

torch::Tensor lut_linear_cpu(
    torch::Tensor x,
    torch::Tensor codes,
    torch::Tensor alpha,
    int64_t i_pad) {
  TORCH_CHECK(!x.is_cuda() && !codes.is_cuda() && !alpha.is_cuda(),
              "TinyLM LUT native v0 is CPU-only");
  TORCH_CHECK(x.scalar_type() == torch::kFloat32,
              "x must be float32, got ", x.scalar_type());
  TORCH_CHECK(codes.scalar_type() == torch::kUInt8,
              "codes must be uint8");
  TORCH_CHECK(alpha.scalar_type() == torch::kFloat32,
              "alpha must be float32");
  TORCH_CHECK(x.dim() >= 2 && codes.dim() == 2,
              "x must be [..., I] and codes must be [O, J]");
  TORCH_CHECK(alpha.dim() == 1 || (alpha.dim() == 2 && alpha.size(1) == 1),
              "native v0 supports per-row alpha only");

  x = x.contiguous();
  codes = codes.contiguous();
  alpha = alpha.contiguous().view({-1});
  const int64_t input = x.size(-1);
  const int64_t output = codes.size(0);
  const int64_t groups = codes.size(1);
  TORCH_CHECK(i_pad == groups * kGroup,
              "i_pad must equal codes.size(1)*5; got ", i_pad,
              " versus ", groups * kGroup);
  TORCH_CHECK(input <= i_pad && i_pad - input < kGroup,
              "input padding must be in [0,4]");
  TORCH_CHECK(alpha.numel() == output,
              "alpha rows must equal output rows");

  const int64_t batch = x.numel() / input;
  auto x2 = x.view({batch, input});
  auto table = torch::empty({batch, groups, kPatterns}, x.options());
  auto result = torch::empty({batch, output}, x.options());
  const float* x_ptr = x2.data_ptr<float>();
  float* table_ptr = table.data_ptr<float>();
  const uint8_t* code_ptr = codes.data_ptr<uint8_t>();
  const float* alpha_ptr = alpha.data_ptr<float>();
  float* result_ptr = result.data_ptr<float>();
  const auto& patterns = pattern_trits();

  at::parallel_for(0, batch * groups, 1, [&](int64_t begin, int64_t end) {
    for (int64_t linear = begin; linear < end; ++linear) {
      const int64_t b = linear / groups;
      const int64_t j = linear % groups;
      float* row = table_ptr + linear * kPatterns;
      const int64_t base = j * kGroup;
      const float* group_ptr = x_ptr + b * input + std::min(base, input);
      for (int64_t pattern = 0; pattern < kPatterns; ++pattern) {
        float sum = 0.0f;
        if (base + kGroup <= input) {
          sum = group_ptr[0] * patterns[pattern][0]
              + group_ptr[1] * patterns[pattern][1]
              + group_ptr[2] * patterns[pattern][2]
              + group_ptr[3] * patterns[pattern][3]
              + group_ptr[4] * patterns[pattern][4];
        } else {
          for (int64_t k = 0; k < kGroup && base + k < input; ++k) {
            sum += group_ptr[k] * static_cast<float>(patterns[pattern][k]);
          }
        }
        row[pattern] = sum;
      }
    }
  });

  at::parallel_for(0, batch * output, 1, [&](int64_t begin, int64_t end) {
    for (int64_t linear = begin; linear < end; ++linear) {
      const int64_t b = linear / output;
      const int64_t o = linear % output;
      const uint8_t* code_row = code_ptr + o * groups;
      float sum = 0.0f;
      for (int64_t j = 0; j < groups; ++j) {
        sum += table_ptr[(b * groups + j) * kPatterns + code_row[j]];
      }
      result_ptr[linear] = sum * alpha_ptr[o];
    }
  });

  std::vector<int64_t> output_shape(x.sizes().begin(), x.sizes().end());
  output_shape.back() = output;
  return result.view(output_shape);
}
}  // namespace

PYBIND11_MODULE(TORCH_EXTENSION_NAME, module) {
  module.def("lut_linear_cpu", &lut_linear_cpu,
             "TinyLM native CPU LUT linear v0 (float32, per-row alpha)");
}

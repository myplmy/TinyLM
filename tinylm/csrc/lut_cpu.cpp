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

const std::array<std::uint8_t, kPatterns>& pattern_carries() {
  // Transition (pattern-1) -> pattern in base 3.  Each trailing digit 2
  // wraps +1 -> -1 (-2*x), then the first non-wrapped digit advances by x.
  // This builds all 243 sums with additions instead of 243*5 multiplies.
  static std::array<std::uint8_t, kPatterns> values{};
  static std::once_flag initialized;
  std::call_once(initialized, []() {
    for (int64_t pattern = 1; pattern < kPatterns; ++pattern) {
      int64_t previous = pattern - 1;
      std::uint8_t carries = 0;
      while (previous % 3 == 2) {
        ++carries;
        previous /= 3;
      }
      values[pattern] = carries;
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
  const auto& carries = pattern_carries();

  at::parallel_for(0, batch * groups, 1, [&](int64_t begin, int64_t end) {
    for (int64_t linear = begin; linear < end; ++linear) {
      const int64_t b = linear / groups;
      const int64_t j = linear % groups;
      float* row = table_ptr + linear * kPatterns;
      const int64_t base = j * kGroup;
      float activation[kGroup] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
      for (int64_t k = 0; k < kGroup && base + k < input; ++k) {
        activation[k] = x_ptr[b * input + base + k];
      }
      float sum = -(activation[0] + activation[1] + activation[2]
                    + activation[3] + activation[4]);
      row[0] = sum;
      for (int64_t pattern = 1; pattern < kPatterns; ++pattern) {
        const int64_t carry = carries[pattern];
        for (int64_t k = 0; k < carry; ++k) {
          sum -= 2.0f * activation[k];
        }
        sum += activation[carry];
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
             "TinyLM native CPU LUT linear v1 (incremental table, float32, per-row alpha)",
             pybind11::call_guard<pybind11::gil_scoped_release>());
}

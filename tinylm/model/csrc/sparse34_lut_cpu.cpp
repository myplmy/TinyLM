#include <torch/extension.h>
#include <ATen/Parallel.h>

#include <algorithm>
#include <cstdint>

namespace {

inline std::uint8_t decode_5bit(const std::uint8_t* row, std::int64_t row_bytes,
                               std::int64_t block_index) {
  const std::int64_t bit = block_index * 5;
  const std::int64_t byte_index = bit >> 3;
  const int shift = static_cast<int>(bit & 7);
  std::uint16_t word = row[byte_index];
  if (shift > 3 && byte_index + 1 < row_bytes) {
    word |= static_cast<std::uint16_t>(row[byte_index + 1]) << 8;
  }
  return static_cast<std::uint8_t>((word >> shift) & 0x1f);
}

}  // namespace

torch::Tensor sparse34_lut_linear_cpu(torch::Tensor x, torch::Tensor packed,
                                      torch::Tensor alpha, std::int64_t in_features,
                                      std::int64_t group_size) {
  TORCH_CHECK(x.device().is_cpu() && packed.device().is_cpu() && alpha.device().is_cpu(),
              "sparse34_lut_linear: CPU tensors required");
  TORCH_CHECK(x.scalar_type() == at::kFloat, "x must be float32");
  TORCH_CHECK(packed.scalar_type() == at::kByte, "packed must be uint8");
  TORCH_CHECK(alpha.scalar_type() == at::kFloat, "alpha must be float32");
  TORCH_CHECK(x.dim() == 2 && packed.dim() == 2 && alpha.dim() == 2,
              "expected x[M,I], packed[O,row_bytes], alpha[O,I/group]");
  TORCH_CHECK(x.is_contiguous() && packed.is_contiguous() && alpha.is_contiguous(),
              "all inputs must be contiguous");
  TORCH_CHECK(in_features > 0 && in_features % 4 == 0 && x.size(1) == in_features,
              "in_features must be positive, divisible by 4, and match x");
  TORCH_CHECK(group_size > 0 && group_size % 4 == 0 && in_features % group_size == 0,
              "group_size must be divisible by 4 and divide in_features");

  const std::int64_t m_size = x.size(0);
  const std::int64_t out_features = packed.size(0);
  TORCH_CHECK(out_features > 0, "out_features must be positive");
  const std::int64_t blocks = in_features / 4;
  const std::int64_t row_bytes = (blocks * 5 + 7) / 8;
  const std::int64_t alpha_groups = in_features / group_size;
  const std::int64_t blocks_per_alpha = group_size / 4;
  TORCH_CHECK(packed.size(1) == row_bytes, "packed row byte count mismatch");
  TORCH_CHECK(alpha.size(0) == out_features && alpha.size(1) == alpha_groups,
              "alpha shape mismatch");

  auto lut = torch::empty({m_size, blocks, 32}, x.options());
  auto output = torch::empty({m_size, out_features}, x.options());
  const float* x_ptr = x.data_ptr<float>();
  float* lut_ptr = lut.data_ptr<float>();

  // 활성값마다 4개 입력으로 32-state table을 한 번 만들고 모든 출력행이 재사용한다.
  at::parallel_for(0, m_size * blocks, 64, [&](std::int64_t begin, std::int64_t end) {
    for (std::int64_t item = begin; item < end; ++item) {
      const std::int64_t m = item / blocks;
      const std::int64_t block = item % blocks;
      const float* values = x_ptr + m * in_features + block * 4;
      float* table = lut_ptr + (m * blocks + block) * 32;
      for (int zero_pos = 0; zero_pos < 4; ++zero_pos) {
        for (int sign_bits = 0; sign_bits < 8; ++sign_bits) {
          float sum = 0.0f;
          int sign_index = 2;
          for (int pos = 0; pos < 4; ++pos) {
            if (pos == zero_pos) {
              continue;
            }
            const float sign = ((sign_bits >> sign_index) & 1) ? 1.0f : -1.0f;
            sum += sign * values[pos];
            --sign_index;
          }
          table[zero_pos * 8 + sign_bits] = sum;
        }
      }
    }
  });

  const std::uint8_t* packed_ptr = packed.data_ptr<std::uint8_t>();
  const float* alpha_ptr = alpha.data_ptr<float>();
  float* out_ptr = output.data_ptr<float>();

  // packed weight를 직접 읽는다. int8/fp32 weight 복원 버퍼는 존재하지 않는다.
  at::parallel_for(0, m_size * out_features, 64,
                   [&](std::int64_t begin, std::int64_t end) {
    for (std::int64_t item = begin; item < end; ++item) {
      const std::int64_t m = item / out_features;
      const std::int64_t out = item % out_features;
      const std::uint8_t* row = packed_ptr + out * row_bytes;
      const float* table = lut_ptr + m * blocks * 32;
      const float* scales = alpha_ptr + out * alpha_groups;
      float acc = 0.0f;
      for (std::int64_t ag = 0; ag < alpha_groups; ++ag) {
        float group_acc = 0.0f;
        const std::int64_t first = ag * blocks_per_alpha;
        const std::int64_t last = first + blocks_per_alpha;
        for (std::int64_t block = first; block < last; ++block) {
          const std::uint8_t code = decode_5bit(row, row_bytes, block);
          group_acc += table[block * 32 + code];
        }
        acc += group_acc * scales[ag];
      }
      out_ptr[m * out_features + out] = acc;
    }
  });
  return output;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, module) {
  module.def("sparse34_lut_linear", &sparse34_lut_linear_cpu,
             "3:4 1.25bpw packed CPU LUT linear",
             pybind11::call_guard<pybind11::gil_scoped_release>());
}

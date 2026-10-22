#pragma once
#include <cstddef>
#include <span>
#include <vector>

namespace recoverx {
// Return all offsets, including overlapping matches. Empty needles are rejected.
std::vector<std::size_t> find_all(std::span<const unsigned char> data,
                                std::span<const unsigned char> needle,
                                std::size_t limit = 4096);
}

#include "signatures.hpp"
#include <algorithm>
#include <stdexcept>

std::vector<std::size_t> recoverx::find_all(std::span<const unsigned char> data,
                                         std::span<const unsigned char> needle,
                                         std::size_t limit) {
    if (needle.empty() || limit > 1000000) throw std::invalid_argument("Invalid signature or limit");
    std::vector<std::size_t> result;
    auto position = data.begin();
    while (position != data.end()) {
        auto found = std::search(position, data.end(), needle.begin(), needle.end());
        if (found == data.end()) break;
        if (result.size() == limit) throw std::length_error("Signature density limit exceeded");
        result.push_back(static_cast<std::size_t>(found - data.begin()));
        position = found + 1;
    }
    return result;
}

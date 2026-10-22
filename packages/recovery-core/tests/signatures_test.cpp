#include "signatures.hpp"
#include <cassert>
#include <stdexcept>
#include <vector>
int main() {
    const std::vector<unsigned char> data{0,1,1,1,0,1,1};
    const std::vector<unsigned char> needle{1,1};
    const auto matches = recoverx::find_all(data,needle);
    assert((matches == std::vector<std::size_t>{1,2,5}));
    assert(recoverx::find_all({},needle).empty());
    bool rejected=false;
    try { recoverx::find_all(data,{}); } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
    rejected=false;
    try { recoverx::find_all(data,needle,1); } catch(const std::length_error&) { rejected=true; }
    assert(rejected);
}

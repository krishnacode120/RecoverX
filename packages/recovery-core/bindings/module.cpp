#include "signatures.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
PYBIND11_MODULE(_recoverx_native, m) {
    m.doc() = "Bounded signature search; no disk writes or file access";
    m.def("find_all", [](py::bytes input, py::bytes signature) {
        const std::string data = input;
        const std::string needle = signature;
        py::gil_scoped_release release;
        return recoverx::find_all(
            {reinterpret_cast<const unsigned char*>(data.data()), data.size()},
            {reinterpret_cast<const unsigned char*>(needle.data()), needle.size()});
    });
}

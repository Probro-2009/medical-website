#include <pybind11/pybind11.h>
#include <pybind11/stl.h>  // For std::vector

namespace py = pybind11;

class RemedyBridge {
public:
    RemedyBridge(py::object predictor) : predictor_instance(predictor) {}

    std::vector<std::string> predict(const std::vector<std::string>& symptoms) {
        return predictor_instance.attr("predict")(symptoms).cast<std::vector<std::string>>();
    }

private:
    py::object predictor_instance;
};

PYBIND11_MODULE(remedy_bridge, m) {
    py::module_::import("remedy_model");
    py::object predictor = py::module_::import("remedy_model").attr("RemedyPredictor")();

    py::class_<RemedyBridge>(m, "RemedyBridge")
        .def(py::init<py::object>())
        .def("predict", &RemedyBridge::predict);

    m.attr("predictor") = predictor;
}

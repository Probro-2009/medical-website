#include <pybind11/embed.h>  // pybind11::scoped_interpreter
#include <iostream>
#include "bindings.cpp"

namespace py = pybind11;

int main() {
    py::scoped_interpreter guard{};
    
    RemedyBridge model(py::module_::import("remedy_model").attr("RemedyPredictor")());

    std::vector<std::string> symptoms;
    std::string input;

    std::cout << "Enter symptoms (type 'done' to finish):\n";
    while (true) {
        std::getline(std::cin, input);
        if (input == "done") break;
        symptoms.push_back(input);
    }

    std::cout << "\nDebug: You entered " << symptoms.size() << " symptoms:\n";
for (const auto& s : symptoms) {
    std::cout << " - " << s << "\n";
}


    auto remedies = model.predict(symptoms);
    std::cout << "\nPredicted Remedies:\n";
    for (const auto& r : remedies) {
        std::cout << " - " << r << "\n";
    }

    return 0;
}

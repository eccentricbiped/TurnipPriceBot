# CMakeList.txt : CMake project for TurnipPrices, include source and define
# project specific logic here.
#
cmake_minimum_required (VERSION 3.8)

project ("TurnipPrices")

# Typically you don't care so much for a third party library's tests to be
# run from your own project's code.
#set(JSON_BuildTests OFF CACHE INTERNAL "")

# Add source to this project's executable.
add_executable (TurnipPrices "TurnipPrices.cpp" "TurnipPrices.h")

#add_subdirectory(json)

#find_package(nlohmann_json 3.2.0 REQUIRED)

#add_library(json ...)

#set_target_properties(json PROPERTIES LINKER_LANGUAGE CXX)

#target_link_libraries(json PRIVATE nlohmann_json::nlohmann_json)

# TODO: Add tests and install targets if needed.
#set_target_properties(${TARGET} PROPERTIES 
#    VS_DEBUGGER_COMMAND_ARGUMENTS "arg1 arg2 arg3")
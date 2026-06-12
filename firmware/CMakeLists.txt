cmake_minimum_required(VERSION 3.16)

# -----------------------------------------------------------------------
# ESP-IDF project entry point
# Source this file from the firmware/ directory:
#   cd firmware && idf.py build
# -----------------------------------------------------------------------

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(openclaw_firmware)

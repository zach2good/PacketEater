cmake_minimum_required(VERSION 3.20)
project(PacketEater C CXX)

if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(STATUS "CMAKE_SIZEOF_VOID_P == 8: 64-bit build")
    message(FATAL_ERROR "64-bit build is not supported. Please clean your build directory and reconfigure with: cmake .. -A Win32")
elseif(CMAKE_SIZEOF_VOID_P EQUAL 4)
    message(STATUS "CMAKE_SIZEOF_VOID_P == 4: 32-bit build")
endif()

message(STATUS "CMAKE_VERSION: ${CMAKE_VERSION}")
message(STATUS "CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}")
message(STATUS "CMAKE_C_COMPILER: ${CMAKE_C_COMPILER}")
message(STATUS "CMAKE_CXX_COMPILER: ${CMAKE_CXX_COMPILER}")
message(STATUS "CMAKE_CXX_COMPILER_ID: ${CMAKE_CXX_COMPILER_ID}")
message(STATUS "CMAKE_CXX_COMPILER_VERSION: ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "CMAKE_CXX_FLAGS: ${CMAKE_CXX_FLAGS}")
message(STATUS "CMAKE_GENERATOR: ${CMAKE_GENERATOR}")
message(STATUS "CMAKE_GENERATOR_PLATFORM: ${CMAKE_GENERATOR_PLATFORM}")

set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_POSITION_INDEPENDENT_CODE OFF)

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
link_libraries(${CMAKE_THREAD_LIBS_INIT})

set(CORE_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/httplib.h
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/task_system.h
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/packet_eater_core.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/packet_eater_core.h
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/base64pp.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/base64pp.h
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/json.hpp
)

set(ASHITA_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/ashita/ashita_plugin.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/ashita/ashita_plugin.h
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/ashita/exports.def
)

add_library(PacketEaterAshita SHARED ${CORE_SOURCES} ${ASHITA_SOURCES})

target_include_directories(PacketEaterAshita PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/3rdParty/SDKs/Ashita/ADK_v4/)

set_property(TARGET PacketEaterAshita PROPERTY CXX_STANDARD 20)
set_property(TARGET PacketEaterAshita PROPERTY CXX_STANDARD_REQUIRED ON)
set_property(TARGET PacketEaterAshita PROPERTY CXX_EXTENSIONS ON)
set_property(TARGET PacketEaterAshita PROPERTY LINKER_LANGUAGE CXX)
set_property(TARGET PacketEaterAshita PROPERTY USE_FOLDERS ON)
set_property(TARGET PacketEaterAshita PROPERTY OUTPUT_NAME "PacketEater")

set(WINDOWER_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/windower/exports.def
    ${CMAKE_CURRENT_SOURCE_DIR}/PacketEater/windower/windower_plugin.cpp
)

add_library(PacketEaterWindower SHARED ${CORE_SOURCES} ${WINDOWER_SOURCES})

target_compile_definitions(PacketEaterWindower PUBLIC -DSOL_ALL_SAFETIES_ON=1)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/3rdParty/sol)

target_include_directories(PacketEaterWindower PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/3rdParty/SDKs/Windower/LUA/
    ${CMAKE_CURRENT_SOURCE_DIR}/3rdParty/sol/include)
target_link_libraries(PacketEaterWindower PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/3rdParty/SDKs/Windower/LuaCore_exports.lib
    sol2_single)

set_property(TARGET PacketEaterWindower PROPERTY CXX_STANDARD 20)
set_property(TARGET PacketEaterWindower PROPERTY CXX_STANDARD_REQUIRED ON)
set_property(TARGET PacketEaterWindower PROPERTY CXX_EXTENSIONS ON)
set_property(TARGET PacketEaterWindower PROPERTY LINKER_LANGUAGE CXX)
set_property(TARGET PacketEaterWindower PROPERTY USE_FOLDERS ON)
set_property(TARGET PacketEaterWindower PROPERTY OUTPUT_NAME "_PacketEater")

function(set_target_output_directory target dir)
    message(STATUS "Setting output directory for ${target} to ${dir}")
    set_target_properties(${target} PROPERTIES
        VS_DEBUGGER_WORKING_DIRECTORY "${dir}"
        RUNTIME_OUTPUT_DIRECTORY_DEBUG "${dir}"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${dir}"
        RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${dir}"
        RUNTIME_OUTPUT_DIRECTORY_MINSIZEREL "${dir}"
    )
endfunction()

set_target_output_directory(PacketEaterAshita "${CMAKE_CURRENT_SOURCE_DIR}/bin/Ashita/")
set_target_output_directory(PacketEaterWindower "${CMAKE_CURRENT_SOURCE_DIR}/bin/Windower/lib/")

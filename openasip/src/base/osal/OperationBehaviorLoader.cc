/*
    Copyright (c) 2002-2009 Tampere University.

    This file is part of TTA-Based Codesign Environment (TCE).

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
 */
/**
 * @file OperationBehaviorLoader.cc
 *
 * Definition of OperationBehaviorLoader class.
 *
 * @author Jussi Nykänen 2004 (nykanen-no.spam-cs.tut.fi)
 * @note rating: yellow
 * @note reviewed 19 August 2004 by pj, jn, ao, ac
 */

#include "OperationBehaviorLoader.hh"
#include "Operation.hh"
#include "OperationBehavior.hh"
#include "OperationIndex.hh"
#include "FileSystem.hh"
#include "StringTools.hh"
#include "OperationModule.hh"
#include "TCEString.hh"

using std::string;

const string OperationBehaviorLoader::CREATE_FUNC = "createOpBehavior_";
const string OperationBehaviorLoader::DELETE_FUNC = "deleteOpBehavior_";

/**
 * Constructor.
 *
 * OperationBehavior uses OperationIndex for getting the right modules.
 *
 * @param index OperationIndex.
 *
 * @note The PluginTools instance should load the behavior modules in the LOCAL
 * mode to enable overriding behavior definitions from later definitions in
 * the search path. E.g., if base.opb defines ADD, a custom.opb can redefine
 * it. If the symbols are made global then the latter symbol is not reloaded
 * but the one from base.opb reused.
 */
OperationBehaviorLoader::OperationBehaviorLoader(OperationIndex& index) :
    index_(index), tools_(false, true) {
}

/**
 * Destructor.
 *
 * Deletes all the loader operation behavior models.
 */
OperationBehaviorLoader::~OperationBehaviorLoader() {
    freeBehavior();
}

/**
 * Imports the behavior model of an operation.
 *
 * First, the module that contains the given operation is obtained from
 * OperationIndex. A pointer to appropriate create function is obtained and
 * used to create OperationBehavior. Also pointer to appropriate destruction
 * function is obtained and stored.
 *
 * @param parent The operation that owns the loaded behavior.
 * @return Operation behavior model of the operation.
 * @exception DynamicLibraryException If an error occurs while accessing the
 *                                    dynamic module.
 * @exception FileNotFound If the .opb was not found.
 * @exception SymbolNotFound If the constructor/destructor functions could
 *            not be imported from the .opb.
 */
OperationBehavior&
OperationBehaviorLoader::importBehavior(const Operation& parent) {
    // Open log file for appending, fallback to stderr if failed
    FILE* log = fopen("/tmp/openasip_importBehavior.log", "a");
    if (log == NULL) {
        log = stderr;
    }

    string name = parent.name();
    fprintf(log, "importBehavior called for operation: %s\n", name.c_str());

    // if behavior was already created, use it
    BehaviorMap::iterator iter = behaviors_.find(name);
    if (iter != behaviors_.end()) {
        fprintf(
            log, "Found existing behavior for %s, reusing\n", name.c_str());
        if (log != stderr) fclose(log);
        return *((*iter).second);
    }
    
    try {
        fprintf(log, "Finding module for operation: %s\n", name.c_str());
        OperationModule& module = index_.moduleOf(name);
        if (&module == &NullOperationModule::instance()) {
            string msg = "Module for operation " + name + " not found";
            fprintf(log, "ERROR: %s\n", msg.c_str());
            if (log != stderr) fclose(log);
            throw InstanceNotFound(__FILE__, __LINE__, __func__, msg);
        }
       
        string creatorName = CREATE_FUNC + StringTools::stringToUpper(name);
        string destructorName = DELETE_FUNC + StringTools::stringToUpper(name);
        string modName = module.behaviorModule();

        fprintf(
            log, "Looking for creator %s and destructor %s in module %s\n",
            creatorName.c_str(), destructorName.c_str(), modName.c_str());

        OperationBehavior* (*behaviorCreator)(const Operation&);
        void (*behaviorDestructor)(OperationBehavior*);

        fprintf(log, "Importing symbol: %s\n", creatorName.c_str());
        tools_.importSymbol(creatorName, behaviorCreator, modName);

        fprintf(log, "Importing symbol: %s\n", destructorName.c_str());
        tools_.importSymbol(destructorName, behaviorDestructor, modName);

        fprintf(
            log, "Creating behavior for %s using imported creator\n",
            name.c_str());
        OperationBehavior* behavior = behaviorCreator(parent);

        fprintf(log, "Storing behavior and destructor in maps\n");
        behaviors_[name] = behavior;
        destructors_[behavior] = behaviorDestructor;

        fprintf(log, "Successfully imported behavior for %s\n", name.c_str());
        if (log != stderr) fclose(log);
        return *behavior;
    
    } catch (const FileNotFound& e) {
        fprintf(
            log, "ERROR: FileNotFound exception: %s\n",
            e.errorMessage().c_str());
        if (log != stderr) fclose(log);
        throw e;
    } catch (const SymbolNotFound& e) {
        fprintf(
            log, "ERROR: SymbolNotFound exception: %s\n",
            e.errorMessage().c_str());
        if (log != stderr) fclose(log);
        throw e;
    } catch (const Exception& e) {
        fprintf(
            log, "ERROR: Exception caught: %s\n", e.errorMessage().c_str());
        string msg = std::string("Behavior definition for ") + parent.name() +
                     " could not be loaded.";
        fprintf(log, "Creating new exception: %s\n", msg.c_str());
        if (log != stderr) fclose(log);
        DynamicLibraryException error(__FILE__, __LINE__, __func__, msg);
        error.setCause(e);
        throw error;
    }
}

/**
 * Frees all the imported behavior models of the operations.
 */
void
OperationBehaviorLoader::freeBehavior() {
    DestructionMap::iterator iter = destructors_.begin();
    while (iter != destructors_.end()) {
        void (*behaviorDestructor)(OperationBehavior*) = (*iter).second;
        behaviorDestructor((*iter).first);
        iter++;
    }
    destructors_.clear();
    behaviors_.clear();
    tools_.unregisterAllModules();
}

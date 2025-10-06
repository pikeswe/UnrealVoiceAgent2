#pragma once

#include "Modules/ModuleManager.h"

class FNovaLinkModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};

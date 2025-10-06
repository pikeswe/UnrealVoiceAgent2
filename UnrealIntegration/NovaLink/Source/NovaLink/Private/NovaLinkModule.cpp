#include "NovaLinkModule.h"
#include "Modules/ModuleManager.h"
#include "WebSocketsModule.h"

IMPLEMENT_MODULE(FNovaLinkModule, NovaLink)

void FNovaLinkModule::StartupModule()
{
    FModuleManager::Get().LoadModuleChecked<FWebSocketsModule>("WebSockets");
}

void FNovaLinkModule::ShutdownModule()
{
}

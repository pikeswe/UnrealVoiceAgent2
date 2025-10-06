#include "AudioReceiver.h"

#include "WebSocketsModule.h"
#include "IWebSocket.h"
#include "Modules/ModuleManager.h"

namespace
{
    const FString DefaultAudioUrl = TEXT("ws://localhost:5000/ws/audio");
}

UAudioReceiver::UAudioReceiver()
    : WebSocketUrl(DefaultAudioUrl)
    , bIsConnected(false)
{
}

void UAudioReceiver::StartConnection(const FString& OptionalOverrideUrl)
{
    FString TargetUrl = OptionalOverrideUrl.IsEmpty() ? WebSocketUrl : OptionalOverrideUrl;

    if (TargetUrl.IsEmpty())
    {
        UE_LOG(LogTemp, Warning, TEXT("NovaLink AudioReceiver requires a websocket URL."));
        return;
    }

    StopConnection();

    FWebSocketsModule* Module = FModuleManager::GetModulePtr<FWebSocketsModule>("WebSockets");
    if (!Module)
    {
        Module = &FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");
    }

    WebSocket = Module->CreateWebSocket(TargetUrl);

    WebSocket->OnConnected().AddUObject(this, &UAudioReceiver::HandleConnected);
    WebSocket->OnConnectionError().AddUObject(this, &UAudioReceiver::HandleConnectionError);
    WebSocket->OnClosed().AddUObject(this, &UAudioReceiver::HandleClosed);
    WebSocket->OnRawMessage().AddUObject(this, &UAudioReceiver::HandleBinaryMessage);

    WebSocket->Connect();
}

void UAudioReceiver::StopConnection()
{
    if (WebSocket.IsValid())
    {
        WebSocket->OnConnected().RemoveAll(this);
        WebSocket->OnConnectionError().RemoveAll(this);
        WebSocket->OnClosed().RemoveAll(this);
        WebSocket->OnRawMessage().RemoveAll(this);

        if (WebSocket->IsConnected())
        {
            WebSocket->Close(1000, TEXT("AudioReceiver Stop"));
        }
    }

    ResetWebSocket();
}

bool UAudioReceiver::IsConnected() const
{
    return bIsConnected;
}

void UAudioReceiver::HandleConnected()
{
    bIsConnected = true;
    OnConnectionStateChanged.Broadcast(true);
}

void UAudioReceiver::HandleConnectionError(const FString& Error)
{
    UE_LOG(LogTemp, Error, TEXT("NovaLink AudioReceiver connection error: %s"), *Error);
    bIsConnected = false;
    OnConnectionStateChanged.Broadcast(false);
    ResetWebSocket();
}

void UAudioReceiver::HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
    bIsConnected = false;
    OnConnectionStateChanged.Broadcast(false);
    ResetWebSocket();
}

void UAudioReceiver::HandleBinaryMessage(const void* Data, SIZE_T Size, SIZE_T BytesRemaining)
{
    if (!Data || Size == 0)
    {
        return;
    }

    const uint8* ByteData = static_cast<const uint8*>(Data);
    TArray<uint8> Buffer;
    Buffer.Append(ByteData, static_cast<int32>(Size));

    OnAudioChunkReceived.Broadcast(Buffer);
}

void UAudioReceiver::ResetWebSocket()
{
    if (WebSocket.IsValid())
    {
        WebSocket.Reset();
    }
    bIsConnected = false;
}

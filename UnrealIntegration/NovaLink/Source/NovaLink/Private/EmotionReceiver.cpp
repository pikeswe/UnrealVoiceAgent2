#include "EmotionReceiver.h"

#include "IWebSocket.h"
#include "JsonUtilities.h"
#include "Modules/ModuleManager.h"
#include "WebSocketsModule.h"

namespace
{
    const FString DefaultEmotionUrl = TEXT("ws://localhost:5000/ws/emotion");
}

UEmotionReceiver::UEmotionReceiver()
    : WebSocketUrl(DefaultEmotionUrl)
    , bIsConnected(false)
{
}

void UEmotionReceiver::StartConnection(const FString& OptionalOverrideUrl)
{
    FString TargetUrl = OptionalOverrideUrl.IsEmpty() ? WebSocketUrl : OptionalOverrideUrl;

    if (TargetUrl.IsEmpty())
    {
        UE_LOG(LogTemp, Warning, TEXT("NovaLink EmotionReceiver requires a websocket URL."));
        return;
    }

    StopConnection();

    FWebSocketsModule* Module = FModuleManager::GetModulePtr<FWebSocketsModule>("WebSockets");
    if (!Module)
    {
        Module = &FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");
    }

    WebSocket = Module->CreateWebSocket(TargetUrl);

    WebSocket->OnConnected().AddUObject(this, &UEmotionReceiver::HandleConnected);
    WebSocket->OnConnectionError().AddUObject(this, &UEmotionReceiver::HandleConnectionError);
    WebSocket->OnClosed().AddUObject(this, &UEmotionReceiver::HandleClosed);
    WebSocket->OnMessage().AddUObject(this, &UEmotionReceiver::HandleMessage);

    WebSocket->Connect();
}

void UEmotionReceiver::StopConnection()
{
    if (WebSocket.IsValid())
    {
        WebSocket->OnConnected().RemoveAll(this);
        WebSocket->OnConnectionError().RemoveAll(this);
        WebSocket->OnClosed().RemoveAll(this);
        WebSocket->OnMessage().RemoveAll(this);

        if (WebSocket->IsConnected())
        {
            WebSocket->Close(1000, TEXT("EmotionReceiver Stop"));
        }
    }

    ResetWebSocket();
}

bool UEmotionReceiver::IsConnected() const
{
    return bIsConnected;
}

void UEmotionReceiver::HandleConnected()
{
    bIsConnected = true;
    OnConnectionStateChanged.Broadcast(true);
}

void UEmotionReceiver::HandleConnectionError(const FString& Error)
{
    UE_LOG(LogTemp, Error, TEXT("NovaLink EmotionReceiver connection error: %s"), *Error);
    bIsConnected = false;
    OnConnectionStateChanged.Broadcast(false);
    ResetWebSocket();
}

void UEmotionReceiver::HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
    bIsConnected = false;
    OnConnectionStateChanged.Broadcast(false);
    ResetWebSocket();
}

void UEmotionReceiver::HandleMessage(const FString& Message)
{
    TMap<FString, float> ParsedValues;
    if (TryParseEmotionMessage(Message, ParsedValues))
    {
        OnEmotionUpdate.Broadcast(FNovaLinkEmotionData(ParsedValues));
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("NovaLink EmotionReceiver received invalid JSON: %s"), *Message);
    }
}

void UEmotionReceiver::ResetWebSocket()
{
    if (WebSocket.IsValid())
    {
        WebSocket.Reset();
    }
    bIsConnected = false;
}

bool UEmotionReceiver::TryParseEmotionMessage(const FString& Message, TMap<FString, float>& OutValues)
{
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    TSharedPtr<FJsonObject> JsonObject;
    if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
    {
        return false;
    }

    OutValues.Reset();
    for (const auto& Pair : JsonObject->Values)
    {
        if (!Pair.Value.IsValid())
        {
            continue;
        }

        double NumericValue = 0.0;
        if (Pair.Value->TryGetNumber(NumericValue))
        {
            OutValues.Add(Pair.Key, static_cast<float>(NumericValue));
        }
        else if (Pair.Value->Type == EJson::String)
        {
            const FString RawString = Pair.Value->AsString();
            if (RawString.IsNumeric())
            {
                OutValues.Add(Pair.Key, FCString::Atof(*RawString));
            }
        }
    }

    return OutValues.Num() > 0;
}

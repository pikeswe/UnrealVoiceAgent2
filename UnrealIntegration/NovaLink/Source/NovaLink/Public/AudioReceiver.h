#pragma once

#include "CoreMinimal.h"
#include "AudioReceiver.generated.h"

class IWebSocket;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNovaLinkAudioChunkReceived, const TArray<uint8>&, AudioChunk);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNovaLinkConnectionStateChanged, bool, bIsConnected);

UCLASS(BlueprintType)
class NOVALINK_API UAudioReceiver : public UObject
{
    GENERATED_BODY()

public:
    UAudioReceiver();

    /** Default websocket URL used if none is provided when starting the connection. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NovaLink|Audio")
    FString WebSocketUrl;

    /** Invoked whenever a binary audio chunk is received from the websocket. */
    UPROPERTY(BlueprintAssignable, Category = "NovaLink|Audio")
    FNovaLinkAudioChunkReceived OnAudioChunkReceived;

    /** Broadcasts whenever the websocket connection opens or closes. */
    UPROPERTY(BlueprintAssignable, Category = "NovaLink|Audio")
    FNovaLinkConnectionStateChanged OnConnectionStateChanged;

    /** Starts the websocket connection. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink|Audio")
    void StartConnection(const FString& OptionalOverrideUrl = TEXT(""));

    /** Stops the websocket connection if active. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink|Audio")
    void StopConnection();

    /** Returns true when the websocket is currently connected. */
    UFUNCTION(BlueprintPure, Category = "NovaLink|Audio")
    bool IsConnected() const;

private:
    void HandleConnected();
    void HandleConnectionError(const FString& Error);
    void HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean);
    void HandleBinaryMessage(const void* Data, SIZE_T Size, SIZE_T BytesRemaining);

    void ResetWebSocket();

    TSharedPtr<IWebSocket> WebSocket;
    bool bIsConnected;
};

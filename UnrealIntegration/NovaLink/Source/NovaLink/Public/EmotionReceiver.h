#pragma once

#include "CoreMinimal.h"
#include "EmotionReceiver.generated.h"

class IWebSocket;

USTRUCT(BlueprintType)
struct NOVALINK_API FNovaLinkEmotionData
{
    GENERATED_BODY()

    FNovaLinkEmotionData() = default;

    explicit FNovaLinkEmotionData(const TMap<FString, float>& InValues)
        : EmotionValues(InValues)
    {
    }

    UPROPERTY(BlueprintReadWrite, Category = "NovaLink|Emotion")
    TMap<FString, float> EmotionValues;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNovaLinkEmotionUpdate, const FNovaLinkEmotionData&, EmotionData);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNovaLinkEmotionConnectionStateChanged, bool, bIsConnected);

UCLASS(BlueprintType)
class NOVALINK_API UEmotionReceiver : public UObject
{
    GENERATED_BODY()

public:
    UEmotionReceiver();

    /** Default websocket URL used if none is provided when starting the connection. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NovaLink|Emotion")
    FString WebSocketUrl;

    /** Invoked whenever a JSON emotion payload arrives. */
    UPROPERTY(BlueprintAssignable, Category = "NovaLink|Emotion")
    FNovaLinkEmotionUpdate OnEmotionUpdate;

    /** Broadcasts whenever the websocket connection opens or closes. */
    UPROPERTY(BlueprintAssignable, Category = "NovaLink|Emotion")
    FNovaLinkEmotionConnectionStateChanged OnConnectionStateChanged;

    /** Starts the websocket connection. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink|Emotion")
    void StartConnection(const FString& OptionalOverrideUrl = TEXT(""));

    /** Stops the websocket connection if active. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink|Emotion")
    void StopConnection();

    /** Returns true when the websocket is currently connected. */
    UFUNCTION(BlueprintPure, Category = "NovaLink|Emotion")
    bool IsConnected() const;

private:
    void HandleConnected();
    void HandleConnectionError(const FString& Error);
    void HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean);
    void HandleMessage(const FString& Message);

    void ResetWebSocket();

    static bool TryParseEmotionMessage(const FString& Message, TMap<FString, float>& OutValues);

    TSharedPtr<IWebSocket> WebSocket;
    bool bIsConnected;
};

#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "NovaLinkFunctionLibrary.generated.h"

class UAudioReceiver;
class UEmotionReceiver;

UCLASS()
class NOVALINK_API UNovaLinkFunctionLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /** Creates a new Audio Receiver object for use in Blueprints. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink", meta = (WorldContext = "WorldContextObject"))
    static UAudioReceiver* CreateAudioReceiver(UObject* WorldContextObject);

    /** Creates a new Emotion Receiver object for use in Blueprints. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink", meta = (WorldContext = "WorldContextObject"))
    static UEmotionReceiver* CreateEmotionReceiver(UObject* WorldContextObject);

    /** Convenience Blueprint node for testing audio connections. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink", meta = (WorldContext = "WorldContextObject"))
    static void ConnectAudio(UObject* WorldContextObject, UAudioReceiver*& OutReceiver, const FString& Url = TEXT("ws://localhost:5000/ws/audio"));

    /** Convenience Blueprint node for testing emotion connections. */
    UFUNCTION(BlueprintCallable, Category = "NovaLink", meta = (WorldContext = "WorldContextObject"))
    static void ConnectEmotion(UObject* WorldContextObject, UEmotionReceiver*& OutReceiver, const FString& Url = TEXT("ws://localhost:5000/ws/emotion"));
};

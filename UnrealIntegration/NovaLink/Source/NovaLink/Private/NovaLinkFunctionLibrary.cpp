#include "NovaLinkFunctionLibrary.h"

#include "AudioReceiver.h"
#include "EmotionReceiver.h"
#include "Engine/World.h"

UAudioReceiver* UNovaLinkFunctionLibrary::CreateAudioReceiver(UObject* WorldContextObject)
{
    if (!WorldContextObject)
    {
        return nullptr;
    }

    return NewObject<UAudioReceiver>(WorldContextObject);
}

UEmotionReceiver* UNovaLinkFunctionLibrary::CreateEmotionReceiver(UObject* WorldContextObject)
{
    if (!WorldContextObject)
    {
        return nullptr;
    }

    return NewObject<UEmotionReceiver>(WorldContextObject);
}

void UNovaLinkFunctionLibrary::ConnectAudio(UObject* WorldContextObject, UAudioReceiver*& OutReceiver, const FString& Url)
{
    OutReceiver = CreateAudioReceiver(WorldContextObject);
    if (OutReceiver)
    {
        OutReceiver->StartConnection(Url);
    }
}

void UNovaLinkFunctionLibrary::ConnectEmotion(UObject* WorldContextObject, UEmotionReceiver*& OutReceiver, const FString& Url)
{
    OutReceiver = CreateEmotionReceiver(WorldContextObject);
    if (OutReceiver)
    {
        OutReceiver->StartConnection(Url);
    }
}

using UnrealBuildTool;

public class NovaLink : ModuleRules
{
    public NovaLink(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "Json",
            "JsonUtilities",
            "AudioMixer"
        });

        PrivateDependencyModuleNames.AddRange(new[]
        {
            "Engine",
            "Slate",
            "SlateCore"
        });
    }
}

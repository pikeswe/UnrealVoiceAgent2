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
            "LiveLinkInterface",
            "WebSockets",
            "Networking",
            "Sockets"
        });

        PrivateDependencyModuleNames.AddRange(new[]
        {
            "Engine",
            "Slate",
            "SlateCore"
        });
    }
}

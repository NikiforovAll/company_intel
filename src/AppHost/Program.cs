var builder = DistributedApplication.CreateBuilder(args);

var ollama = builder
    .AddOllama("ollama")
    .WithImageTag("latest")
    .WithDataVolume()
    .WithLifetime(ContainerLifetime.Persistent)
    .AddModel("qwen3:latest");

var qdrant = builder.AddQdrant("qdrant").WithLifetime(ContainerLifetime.Persistent);

var agent = builder
    .AddUvicornApp("company-intel-agent", "../agent", "main:app")
    .WithUv()
    .WithHttpHealthCheck("/health")
    .WithReference(ollama)
    .WithReference(qdrant)
    .WithOtlpExporter();

var ui = builder
    .AddNpmApp("ui", "../ui", "dev")
    .WithPnpmPackageInstallation()
    .WithHttpEndpoint(port: 3000, env: "PORT")
    .WithEnvironment("AGENT_URL", agent.GetEndpoint("http"))
    .WithEnvironment("NODE_TLS_REJECT_UNAUTHORIZED", "0")
    .WithOtlpExporter();

await builder.Build().RunAsync();

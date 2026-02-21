var builder = DistributedApplication.CreateBuilder(args);

var ollama = builder
    .AddOllama("ollama")
    .WithImageTag("latest")
    .WithDataVolume()
    .WithLifetime(ContainerLifetime.Persistent);

var qwen3 = ollama.AddModel("qwen3:latest");
var embedModel = ollama.AddModel("snowflake-arctic-embed:33m");

var qdrant = builder
    .AddQdrant("qdrant", apiKey: builder.AddParameter("qdrant-apikey", "localdev"))
    .WithLifetime(ContainerLifetime.Persistent);

var agent = builder
    .AddUvicornApp("company-intel-agent", "../agent", "main:app")
    .WithUv()
    .WithHttpHealthCheck("/health")
    .WithReference(qwen3)
    .WithReference(embedModel)
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

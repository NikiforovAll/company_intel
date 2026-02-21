using System.Net;
using Aspire.Hosting.Testing;
using Xunit;

namespace AppHost.Tests;

public class AgentHealthTests
{
    private static readonly TimeSpan DefaultTimeout = TimeSpan.FromMinutes(5);

    [Fact]
    public async Task AgentHealthEndpointReturnsOk()
    {
        using var cts = new CancellationTokenSource(DefaultTimeout);

        var appHost = await DistributedApplicationTestingBuilder.CreateAsync<Projects.AppHost>(
            cts.Token
        );

        await using var app = await appHost.BuildAsync(cts.Token);
        await app.StartAsync(cts.Token);

        await app.ResourceNotifications.WaitForResourceHealthyAsync("agent", cts.Token);

        using var httpClient = app.CreateHttpClient("agent");
        var response = await httpClient.GetAsync("/health", cts.Token);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}

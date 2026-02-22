using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Aspire.Hosting.Testing;
using Xunit;
using Xunit.Abstractions;

namespace AppHost.Tests;

public class RetrievalEvalTests(ITestOutputHelper output)
{
    private static readonly TimeSpan Timeout = TimeSpan.FromMinutes(10);
    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(15);

    [Fact]
    public async Task RetrievalQualityMeetsThresholds()
    {
        using var cts = new CancellationTokenSource(Timeout);
        var appHost = await DistributedApplicationTestingBuilder.CreateAsync<Projects.AppHost>(
            ["UseVolumes=false"],
            (appOptions, _) => appOptions.DisableDashboard = true,
            cts.Token
        );

        await using var app = await appHost.BuildAsync(cts.Token);
        await app.StartAsync(cts.Token);

        await app.ResourceNotifications.WaitForResourceHealthyAsync(
            "company-intel-agent",
            cts.Token
        );

        using var http = app.CreateHttpClient("company-intel-agent");
        http.Timeout = TimeSpan.FromMinutes(5);

        // 1. Start eval (returns 202 immediately)
        var startResp = await http.PostAsJsonAsync(
            "/eval/run",
            new { company = "paypal" },
            cts.Token
        );
        Assert.Equal(HttpStatusCode.Accepted, startResp.StatusCode);
        var runInfo = await startResp.Content.ReadFromJsonAsync<EvalRunInfo>(JsonOpts, cts.Token);
        Assert.NotNull(runInfo);
        output.WriteLine($"Eval started: {runInfo.RunId}");

        // 2. Poll until completed
        EvalStatus? status = null;
        while (!cts.Token.IsCancellationRequested)
        {
            await Task.Delay(PollInterval, cts.Token);
            var statusResp = await http.GetAsync($"/eval/status?run_id={runInfo.RunId}", cts.Token);
            status = await statusResp.Content.ReadFromJsonAsync<EvalStatus>(JsonOpts, cts.Token);
            output.WriteLine($"  [{status?.Phase}] {status?.Progress}");
            if (status?.Status is "completed" or "failed")
                break;
        }

        Assert.NotNull(status);
        if (status.Error is not null)
            output.WriteLine($"  Error: {status.Error}");
        Assert.Equal("completed", status.Status);

        // 3. Report
        output.WriteLine($"\n=== RAG Eval Report: paypal ===");
        output.WriteLine($"  Hit Rate:       {status.Metrics?.HitRate:F2}");
        output.WriteLine($"  Context Recall: {status.Metrics?.ContextRecall:F2}");

        // 4. Assert thresholds (substring match, calibrate after first run)
        Assert.True(
            status.Metrics!.HitRate >= 0.50,
            $"Hit Rate {status.Metrics.HitRate:F2} < 0.50"
        );
        Assert.True(
            status.Metrics!.ContextRecall >= 0.50,
            $"Context Recall {status.Metrics.ContextRecall:F2} < 0.50"
        );
    }

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    private record EvalRunInfo(string RunId, string Status);

    private record EvalStatus(
        string RunId,
        string Status,
        string Phase,
        string Progress,
        string? Error,
        EvalMetrics? Metrics
    );

    private record EvalMetrics(
        [property: JsonPropertyName("hit_rate")] double HitRate,
        [property: JsonPropertyName("context_recall")] double ContextRecall
    );
}

using System.Text.Json;
using System.Text.Json.Serialization;

var value = new ProbeValue(
    new DateTimeOffset(2026, 10, 2, 9, 0, 0, TimeSpan.Zero),
    10.50m,
    null);
var omitNull = new JsonSerializerOptions {
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
};
var output = new {
    stack = ".NET",
    runtime = Environment.Version.ToString(),
    library = "System.Text.Json",
    options = "default and DefaultIgnoreCondition.WhenWritingNull",
    observed = new {
        serializedDefault = JsonSerializer.Serialize(value),
        serializedOmitNull = JsonSerializer.Serialize(value, omitNull),
    },
};
Console.WriteLine(JsonSerializer.Serialize(output));

record ProbeValue(DateTimeOffset Datetime, decimal Decimal, string? Note);

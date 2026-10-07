import com.fasterxml.jackson.annotation.JsonInclude
import com.fasterxml.jackson.databind.ObjectMapper
import java.math.BigDecimal
import java.time.Instant
import java.time.OffsetDateTime

fun main() {
    val mapper = ObjectMapper()
    val omitNulls = ObjectMapper().setSerializationInclusion(JsonInclude.Include.NON_NULL)
    val instant = Instant.parse("2026-10-02T09:00:00Z")
    val offset = OffsetDateTime.parse("2026-10-02T09:00:00Z")
    val defaultValue = linkedMapOf<String, Any?>("note" to null)
    val output = linkedMapOf<String, Any?>(
        "stack" to "Kotlin/JVM",
        "runtime" to System.getProperty("java.runtime.version"),
        "library" to "Jackson Databind 2.11.1",
        "options" to "ObjectMapper defaults; NON_NULL for omit-null comparison",
        "observed" to linkedMapOf(
            "instant" to instant.toString(),
            "offsetDateTime" to offset.toString(),
            "decimalSerialized" to mapper.writeValueAsString(BigDecimal("10.50")),
            "serializedDefault" to mapper.writeValueAsString(defaultValue),
            "serializedOmitNull" to omitNulls.writeValueAsString(defaultValue),
        ),
    )
    println(mapper.writeValueAsString(output))
}

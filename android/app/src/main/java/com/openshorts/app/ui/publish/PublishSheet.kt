package com.openshorts.app.ui.publish

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.openshorts.app.ui.components.BrassButton
import com.openshorts.app.ui.components.LabeledField
import com.openshorts.app.ui.theme.Brass
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * Shared bottom sheet: pick platforms (Instagram / TikTok / YouTube),
 * caption + title, and optionally schedule the post for a future date/time.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PublishSheet(
    title: String,
    defaultDescription: String? = null,
    publishing: Boolean,
    onDismiss: () -> Unit,
    onPublish: (title: String, description: String, platforms: List<String>, scheduledDate: String?, timezone: String?) -> Unit,
) {
    val platforms = listOf("instagram", "tiktok", "youtube")
    var selectedPlatforms by remember { mutableStateOf(setOf("instagram")) }
    var caption by remember { mutableStateOf(defaultDescription ?: "") }
    var postTitle by remember { mutableStateOf("") }
    var schedule by remember { mutableStateOf(false) }
    var timezone by remember { mutableStateOf("Asia/Kolkata") }

    var showDatePicker by remember { mutableStateOf(false) }
    var pickedDate by remember { mutableStateOf<LocalDate?>(null) }
    var pickedHour by remember { mutableStateOf(LocalTime.now().plusHours(1).hour.toString()) }
    var pickedMinute by remember { mutableStateOf(LocalTime.now().minute.toString()) }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurface)

            Text("Platforms", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Row(horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                platforms.forEach { platform ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = platform in selectedPlatforms,
                            onCheckedChange = { checked ->
                                selectedPlatforms = if (checked) selectedPlatforms + platform else selectedPlatforms - platform
                            },
                        )
                        Text(platform, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }

            LabeledField(
                label = "Caption (shown on Instagram/TikTok)",
                value = caption,
                onValueChange = { caption = it },
                singleLine = false,
            )
            LabeledField(
                label = "Title (YouTube)",
                value = postTitle,
                onValueChange = { postTitle = it },
            )

            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = schedule, onCheckedChange = { schedule = it })
                Text("Schedule for later", style = MaterialTheme.typography.bodyMedium)
            }

            if (schedule) {
                LabeledField(label = "Timezone (IANA)", value = timezone, onValueChange = { timezone = it })
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = { showDatePicker = true }) {
                        Text(
                            pickedDate?.format(DateTimeFormatter.ISO_LOCAL_DATE) ?: "Pick date",
                            color = Brass,
                        )
                    }
                    Spacer(Modifier.height(0.dp))
                    LabeledField(
                        label = "Hour",
                        value = pickedHour,
                        onValueChange = { v -> pickedHour = v.filter(Char::isDigit).take(2) },
                        modifier = Modifier.weight(1f),
                    )
                    LabeledField(
                        label = "Min",
                        value = pickedMinute,
                        onValueChange = { v -> pickedMinute = v.filter(Char::isDigit).take(2) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }

            BrassButton(
                text = if (schedule) "Schedule post" else "Publish now",
                icon = Icons.Default.Send,
                enabled = selectedPlatforms.isNotEmpty(),
                loading = publishing,
                onClick = {
                    val scheduledDate = if (schedule && pickedDate != null) {
                        val hh = pickedHour.toIntOrNull()?.coerceIn(0, 23) ?: 0
                        val mm = pickedMinute.toIntOrNull()?.coerceIn(0, 59) ?: 0
                        val time = LocalTime.of(hh, mm)
                        "${pickedDate!!.format(DateTimeFormatter.ISO_LOCAL_DATE)}T${time.format(DateTimeFormatter.ofPattern("HH:mm:ss"))}"
                    } else null
                    onPublish(
                        postTitle.trim(),
                        caption.trim(),
                        selectedPlatforms.toList(),
                        scheduledDate,
                        timezone.takeIf { it.isNotBlank() } ?: "UTC",
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            )

            Text(
                "Posts are sent through OpenShorts → Upload-Post. Make sure Instagram is connected on the server (Social tab).",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }

    if (showDatePicker) {
        val state = rememberDatePickerState(
            initialSelectedDateMillis = pickedDate?.atStartOfDay(ZoneOffset.UTC)?.toInstant()?.toEpochMilli()
                ?: Instant.now().toEpochMilli()
        )
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { millis ->
                        pickedDate = Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate()
                    }
                    showDatePicker = false
                }) { Text("OK") }
            },
            dismissButton = {
                TextButton(onClick = { showDatePicker = false }) { Text("Cancel") }
            },
        ) {
            DatePicker(state = state)
        }
    }
}

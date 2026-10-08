package io.cryptoplatform.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.cryptoplatform.app.domain.model.SevenTimeframeLadder
import io.cryptoplatform.app.ui.theme.*

@Composable
fun StatusBadge(
    text: String,
    backgroundColor: Color,
    textColor: Color,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .background(backgroundColor, RoundedCornerShape(4.dp))
            .border(1.dp, textColor.copy(alpha = 0.3f), RoundedCornerShape(4.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(
            text = text,
            color = textColor,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace
        )
    }
}

@Composable
fun MetricCard(
    label: String,
    value: String,
    subtext: String? = null,
    modifier: Modifier = Modifier,
    valueColor: Color = TextPrimary
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = BgSurface),
        shape = RoundedCornerShape(8.dp),
        border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = label.uppercase(),
                color = TextMuted,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                color = valueColor,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace
            )
            if (subtext != null) {
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = subtext,
                    color = TextMuted,
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
fun SevenTimeframeLadderView(
    ladder: SevenTimeframeLadder,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        ladder.nodes.forEach { node ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .background(BgSurface, RoundedCornerShape(4.dp))
                    .border(1.dp, BorderLight, RoundedCornerShape(4.dp))
                    .padding(vertical = 6.dp, horizontal = 2.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = node.timeframe,
                        color = BrandSky,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = node.state,
                        color = if (node.isBullish) PositiveEmerald else WarningAmber,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }
}

@Composable
fun FinancialCanvasChart(
    points: List<Float> = listOf(10f, 15f, 12f, 22f, 20f, 35f, 30f, 45f),
    modifier: Modifier = Modifier,
    lineColor: Color = BrandBlue
) {
    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(130.dp)
            .background(BgSurface, RoundedCornerShape(6.dp))
            .border(1.dp, BorderLight, RoundedCornerShape(6.dp))
    ) {
        val width = size.width
        val height = size.height

        // Horizontal grid lines
        for (i in 1..3) {
            val y = height * (i / 4f)
            drawLine(
                color = BorderLight,
                start = Offset(0f, y),
                end = Offset(width, y),
                strokeWidth = 1f
            )
        }

        if (points.size < 2) return@Canvas

        val max = points.maxOrNull() ?: 1f
        val min = points.minOrNull() ?: 0f
        val range = if (max == min) 1f else max - min

        val path = Path()
        points.forEachIndexed { index, p ->
            val x = (index.toFloat() / (points.size - 1)) * width
            val normalized = (p - min) / range
            val y = height - (normalized * (height * 0.75f) + height * 0.12f)

            if (index == 0) {
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }
        }

        drawPath(
            path = path,
            color = lineColor,
            style = Stroke(width = 3f)
        )
    }
}

@Composable
fun EmergencyStopDialog(
    isOpen: Boolean,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit
) {
    if (isOpen) {
        AlertDialog(
            onDismissRequest = onDismiss,
            title = {
                Text("🛑 EMERGENCY STOP", fontWeight = FontWeight.Bold, color = AlertRed)
            },
            text = {
                Text(
                    "Immediately halt all trading operations, cancel active paper intents, and transition the trading engine to fail-closed safe mode?",
                    color = TextPrimary
                )
            },
            confirmButton = {
                Button(
                    onClick = onConfirm,
                    colors = ButtonDefaults.buttonColors(containerColor = AlertRed)
                ) {
                    Text("HALT SYSTEM", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = onDismiss) {
                    Text("Cancel", color = TextSecondary)
                }
            },
            containerColor = BgSurface,
            shape = RoundedCornerShape(8.dp)
        )
    }
}

package io.cryptoplatform.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.cryptoplatform.app.ui.components.StatusBadge
import io.cryptoplatform.app.ui.theme.*
import io.cryptoplatform.app.ui.viewmodel.AccountViewModel

@Composable
fun AccountScreen(
    viewModel: AccountViewModel,
    onTriggerEmergencyStop: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()
    var isAuthDialogOpen by remember { mutableStateOf(false) }
    var isRegisterMode by remember { mutableStateOf(false) }

    var inputName by remember { mutableStateOf("") }
    var inputEmail by remember { mutableStateOf("") }
    var inputPassword by remember { mutableStateOf("") }
    var inputConfirm by remember { mutableStateOf("") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // User Profile Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Operator Account", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        StatusBadge(
                            text = if (state.isAuthenticated) "AUTHENTICATED" else "DEMO MODE",
                            backgroundColor = BrandBlue.copy(alpha = 0.1f),
                            textColor = BrandBlue
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("User: ${state.username}", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    Text("Email: ${state.email}", fontSize = 12.sp, color = TextMuted)
                    Text("Tenant ID: ${state.tenantId} (Isolated)", fontSize = 12.sp, color = TextMuted, fontFamily = FontFamily.Monospace)

                    Spacer(modifier = Modifier.height(10.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(
                            onClick = { viewModel.logout() },
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Log Out", fontSize = 12.sp)
                        }
                        Button(
                            onClick = { isAuthDialogOpen = true },
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Switch Account", fontSize = 12.sp)
                        }
                    }

                    state.message?.let { msg ->
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(msg, fontSize = 11.sp, color = BrandBlue, fontFamily = FontFamily.Monospace)
                    }
                }
            }
        }

        // Emergency Stop & Safety Action
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BgSurface),
                shape = RoundedCornerShape(8.dp),
                border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(BorderLight))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Emergency Stop & Operations", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Immediately halt all simulated operations, pause paper execution, and transition system into fail-closed safe state.",
                        fontSize = 12.sp,
                        color = TextMuted
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Button(
                        onClick = onTriggerEmergencyStop,
                        colors = ButtonDefaults.buttonColors(containerColor = AlertRed),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("🛑 Trigger Emergency Stop", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }

    // Authentication Dialog
    if (isAuthDialogOpen) {
        AlertDialog(
            onDismissRequest = { isAuthDialogOpen = false },
            title = {
                Text(if (isRegisterMode) "Register Account" else "Sign In", fontWeight = FontWeight.Bold)
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (isRegisterMode) {
                        OutlinedTextField(
                            value = inputName,
                            onValueChange = { inputName = it },
                            placeholder = { Text("Full Name") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                    }
                    OutlinedTextField(
                        value = inputEmail,
                        onValueChange = { inputEmail = it },
                        placeholder = { Text("Email Address") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = inputPassword,
                        onValueChange = { inputPassword = it },
                        placeholder = { Text("Password") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    if (isRegisterMode) {
                        OutlinedTextField(
                            value = inputConfirm,
                            onValueChange = { inputConfirm = it },
                            placeholder = { Text("Confirm Password") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                    }
                    Text(
                        text = if (isRegisterMode) "Already have an account? Sign in" else "Need an account? Register",
                        color = BrandBlue,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.clickable { isRegisterMode = !isRegisterMode }
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (isRegisterMode) {
                            viewModel.register(inputName, inputEmail, inputPassword, inputConfirm)
                        } else {
                            viewModel.login(inputEmail, inputPassword)
                        }
                        isAuthDialogOpen = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBlue)
                ) {
                    Text(if (isRegisterMode) "Register" else "Login")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { isAuthDialogOpen = false }) {
                    Text("Cancel")
                }
            },
            containerColor = BgSurface
        )
    }
}

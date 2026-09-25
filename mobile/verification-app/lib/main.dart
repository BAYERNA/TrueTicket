import 'package:flutter/material.dart';

import 'screens/login_screen.dart';

void main() {
  runApp(const TrueTicketVerificationApp());
}

class TrueTicketVerificationApp extends StatelessWidget {
  const TrueTicketVerificationApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TrueTicket 현장 검표',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF1D4ED8),
        useMaterial3: true,
      ),
      home: const LoginScreen(),
    );
  }
}

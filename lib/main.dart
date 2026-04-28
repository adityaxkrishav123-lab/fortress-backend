import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/splash_screen.dart';

import 'package:fortress_mobile/services/mailbox_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await MailboxService.init();
  runApp(const FortressApp());
}

class FortressApp extends StatelessWidget {
  const FortressApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Fortress',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const SplashScreen(),
    );
  }
}

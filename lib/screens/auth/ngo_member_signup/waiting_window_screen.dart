import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/splash_screen.dart';

class WaitingWindowScreen extends StatelessWidget {
  const WaitingWindowScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(40.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(32),
                      decoration: BoxDecoration(
                        color: AppTheme.tealPrimary.withOpacity(0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.hourglass_empty_rounded, size: 80, color: AppTheme.tealPrimary),
                    ),
                    const SizedBox(height: 48),
                    const Text(
                      'Waiting for Approval',
                      style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Pls wait till Admin assigns you your work and Power.',
                      style: TextStyle(fontSize: 16, color: Colors.grey, height: 1.5),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 60),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppTheme.tealPrimary),
                        minimumSize: const Size(double.infinity, 56),
                      ),
                      onPressed: () {
                        Navigator.of(context).pushAndRemoveUntil(
                          MaterialPageRoute(builder: (context) => const SplashScreen()),
                          (route) => false,
                        );
                      },
                      child: const Text('Back to Home', style: TextStyle(color: AppTheme.tealPrimary)),
                    ),
                  ],
                ),
              ),
            ),
            _buildProgressDots(2),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressDots(int currentIndex) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(3, (index) {
          return Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: index == currentIndex ? Colors.black : Colors.grey.shade400,
            ),
          );
        }),
      ),
    );
  }
}

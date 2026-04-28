import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/splash_screen.dart';

class AdminPinSetupScreen extends StatefulWidget {
  const AdminPinSetupScreen({super.key});

  @override
  State<AdminPinSetupScreen> createState() => _AdminPinSetupScreenState();
}

class _AdminPinSetupScreenState extends State<AdminPinSetupScreen> {
  String _pin = '';

  void _onKeyPress(String key) {
    if (_pin.length < 6) {
      setState(() {
        _pin += key;
      });
      if (_pin.length == 6) {
        // PIN Set logic via Nodepoint
      }
    }
  }

  void _onDelete() {
    if (_pin.isNotEmpty) {
      setState(() {
        _pin = _pin.substring(0, _pin.length - 1);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Security Setup'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppTheme.navySecondary),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 20),
            const Icon(Icons.security_rounded, size: 64, color: AppTheme.tealPrimary),
            const SizedBox(height: 24),
            const Text(
              'Create Security PIN',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
            ),
            const SizedBox(height: 12),
            const Text(
              'Set a 6-digit PIN for your NGO Admin account',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 48),
            
            // PIN Dots
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(6, (index) {
                bool isFilled = index < _pin.length;
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 10),
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isFilled ? AppTheme.tealPrimary : Colors.grey[300],
                    border: isFilled ? null : Border.all(color: Colors.grey[400]!),
                  ),
                );
              }),
            ),
            
            const Spacer(),
            
            // Number Pad
            _buildNumberPad(),
            
            const SizedBox(height: 40),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: ElevatedButton(
                onPressed: _pin.length == 6 ? () {
                  // Finalize and go back to Splash as per 6 -> 1 path
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (context) => const SplashScreen()),
                    (route) => false,
                  );
                } : null,
                child: const Text('Finish Registration'),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildNumberPad() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: ['1', '2', '3'].map((e) => _buildKey(e)).toList(),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: ['4', '5', '6'].map((e) => _buildKey(e)).toList(),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: ['7', '8', '9'].map((e) => _buildKey(e)).toList(),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const SizedBox(width: 60),
              _buildKey('0'),
              _buildDeleteKey(),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildKey(String key) {
    return InkWell(
      onTap: () => _onKeyPress(key),
      borderRadius: BorderRadius.circular(30),
      child: Container(
        width: 60,
        height: 60,
        alignment: Alignment.center,
        child: Text(
          key,
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
        ),
      ),
    );
  }

  Widget _buildDeleteKey() {
    return InkWell(
      onTap: _onDelete,
      borderRadius: BorderRadius.circular(30),
      child: Container(
        width: 60,
        height: 60,
        alignment: Alignment.center,
        child: const Icon(Icons.backspace_outlined, color: Colors.grey),
      ),
    );
  }
}

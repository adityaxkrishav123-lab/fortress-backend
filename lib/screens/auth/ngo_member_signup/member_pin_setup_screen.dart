import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/dashboard/dashboard_screen.dart';

class MemberPinSetupScreen extends StatefulWidget {
  const MemberPinSetupScreen({super.key});

  @override
  State<MemberPinSetupScreen> createState() => _MemberPinSetupScreenState();
}

class _MemberPinSetupScreenState extends State<MemberPinSetupScreen> {
  final _pinController = TextEditingController();
  final _confirmPinController = TextEditingController();

  @override
  void dispose() {
    _pinController.dispose();
    _confirmPinController.dispose();
    super.dispose();
  }

  void _onSubmit() {
    if (_pinController.text != _confirmPinController.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PINs do not match!'), backgroundColor: Colors.red),
      );
      return;
    }
    // Success path 10 -> 1 -> 7 (Direct to Dashboard in Phase 5)
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (context) => const DashboardScreen(
        role: 'NGO_MEMBER',
        userName: 'Member User',
      )),
      (route) => false,
    );
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
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Set Member Access PIN', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primaryColor)),
                  const SizedBox(height: 12),
                  const Text('Create a 6-digit PIN to access your NGO dashboard.', style: TextStyle(color: Colors.white70)),
                  const SizedBox(height: 48),
                  
                  const Text('Set 6 digit pin *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  _buildPinField(_pinController),
                  const SizedBox(height: 16),
                  const Text('Confirm pin *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  _buildPinField(_confirmPinController),
                  
                  const SizedBox(height: 60),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryColor,
                      foregroundColor: Colors.black,
                    ),
                    onPressed: _onSubmit,
                    child: const Text('Finish & Submit'),
                  ),
                ],
              ),
            ),
          ),
          _buildProgressDots(1),
        ],
      ),
    );
  }


  Widget _buildPinField(TextEditingController controller) {
    return TextField(
      controller: controller,
      obscureText: true,
      keyboardType: TextInputType.number,
      maxLength: 6,
      decoration: const InputDecoration(
        counterText: '',
        hintText: '● ● ● ● ● ●',
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

import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/services/api_service.dart';
import 'package:fortress_mobile/screens/dashboard/dashboard_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phoneController = TextEditingController(text: '9000000001'); // Default to Sam Citizen
  String _pin = '';
  bool _isLoading = false;

  Future<void> _onKeyPress(String key) async {
    if (_pin.length < 6 && !_isLoading) {
      setState(() {
        _pin += key;
      });
      if (_pin.length == 6) {
        setState(() { _isLoading = true; });
        try {
          // Dynamically use the phone number entered in the field
          final result = await ApiService.login('+91${_phoneController.text}', _pin);
          
          if (!mounted) return;
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => DashboardScreen(
                role: result['user']['role'],
                userName: result['user']['name'],
                rank: result['user']['rank'] ?? 'Agent',
              ),
            ),
          );
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('INVALID SECURE PIN. ACCESS DENIED.'),
              backgroundColor: Colors.red,
            ),
          );
          setState(() {
            _pin = '';
            _isLoading = false;
          });
        }
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
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 60),
            const Icon(Icons.lock_person_rounded, size: 64, color: AppTheme.primaryColor),
            const SizedBox(height: 24),
            Text('Enter Secure PIN', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 12),
            const Text('Enter your 6-digit access code', style: TextStyle(color: Colors.white70)),
            const SizedBox(height: 32),
            
            // Phone Number Input for Demo
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 60),
              child: TextField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.primaryColor, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 2),
                decoration: InputDecoration(
                  prefixText: '+91 ',
                  prefixStyle: const TextStyle(color: Colors.white54, fontSize: 16),
                  hintText: 'Phone Number',
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.1)),
                  enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: Colors.white10)),
                  focusedBorder: const UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.primaryColor)),
                ),
              ),
            ),
            
            const SizedBox(height: 32),
            
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
                    color: isFilled ? AppTheme.primaryColor : Colors.white10,
                    border: isFilled ? null : Border.all(color: Colors.white24),
                    boxShadow: isFilled ? [
                      BoxShadow(color: AppTheme.primaryColor.withOpacity(0.5), blurRadius: 10, spreadRadius: 2)
                    ] : null,
                  ),
                );
              }),
            ),
            
            const Spacer(),
            
            // Number Pad
            _buildNumberPad(),
            
            const SizedBox(height: 20),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: RichText(
                text: const TextSpan(
                  text: "New here? ",
                  style: TextStyle(color: Colors.white54),
                  children: [
                    TextSpan(
                      text: 'Create Account',
                      style: TextStyle(color: AppTheme.primaryColor, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
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
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
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

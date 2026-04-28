import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/auth/ngo_member_signup/member_pin_setup_screen.dart';

class NGOMemberSignupScreen extends StatefulWidget {
  const NGOMemberSignupScreen({super.key});

  @override
  State<NGOMemberSignupScreen> createState() => _NGOMemberSignupScreenState();
}

class _NGOMemberSignupScreenState extends State<NGOMemberSignupScreen> {
  final _nameController = TextEditingController();
  final _contactController = TextEditingController();
  final _emailController = TextEditingController();
  final _referralController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _contactController.dispose();
    _emailController.dispose();
    _referralController.dispose();
    super.dispose();
  }

  void _onNext() {
    if (_nameController.text.isEmpty || 
        _contactController.text.isEmpty || 
        _emailController.text.isEmpty || 
        _referralController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All fields are mandatory!'), backgroundColor: Colors.red),
      );
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(builder: (context) => const MemberPinSetupScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Ngo member Signup'),
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
                  const Text('Member Signup form', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
                  const SizedBox(height: 8),
                  const Text('* all fields are mandatory', style: TextStyle(color: Colors.red, fontSize: 12)),
                  const SizedBox(height: 32),
                  
                  _buildTextField('Name', _nameController, Icons.person_outline_rounded, isMandatory: true),
                  const SizedBox(height: 16),
                  
                  // Indian Style Contact No
                  const Row(
                    children: [
                      Text('Contact no', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                      Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _contactController,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.phone_android_rounded, color: AppTheme.tealPrimary),
                      prefixText: '+91 ',
                      hintText: '10-digit number',
                    ),
                  ),
                  
                  const SizedBox(height: 16),
                  _buildTextField('Email', _emailController, Icons.email_outlined, isMandatory: true),
                  const SizedBox(height: 16),
                  
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Text('Referral Code', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                          Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                          Spacer(),
                          Icon(Icons.info_outline_rounded, size: 16, color: AppTheme.tealPrimary),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _referralController,
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.qr_code_rounded, color: AppTheme.tealPrimary),
                          hintText: 'Enter code from Admin',
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 48),
                  ElevatedButton(
                    onPressed: _onNext,
                    child: const Text('Next: Set PIN'),
                  ),
                ],
              ),
            ),
          ),
          _buildProgressDots(0),
        ],
      ),
    );
  }

  Widget _buildTextField(String label, TextEditingController controller, IconData icon, {bool isMandatory = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            if (isMandatory) const Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: InputDecoration(
            prefixIcon: Icon(icon, color: AppTheme.tealPrimary),
            hintText: 'Enter $label',
          ),
        ),
      ],
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

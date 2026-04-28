import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/auth/ngo_admin_signup/specialization_pin_screen.dart';

class OrgDetailsScreen extends StatefulWidget {
  final int tier;
  const OrgDetailsScreen({super.key, required this.tier});

  @override
  State<OrgDetailsScreen> createState() => _OrgDetailsScreenState();
}

class _OrgDetailsScreenState extends State<OrgDetailsScreen> {
  final _aadharController = TextEditingController();
  final _panController = TextEditingController();

  @override
  void dispose() {
    _aadharController.dispose();
    _panController.dispose();
    super.dispose();
  }

  void _onVerify() {
    if (_aadharController.text.isEmpty || _panController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Aadhar and PAN numbers are mandatory!'), backgroundColor: Colors.red),
      );
      return;
    }
    // Simulation: In real app, we'd also check if files are uploaded.
    Navigator.of(context).push(
      MaterialPageRoute(builder: (context) => const SpecializationPinScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Identity Verification'),
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
                  Text(
                    widget.tier == 1 ? 'Step 3: Tier 1 Verification' : 'Step 3: Tier 2 Verification (Scrollable)',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
                  ),
                  const SizedBox(height: 8),
                  const Text('* fields are mandatory', style: TextStyle(color: Colors.red, fontSize: 12)),
                  const SizedBox(height: 24),
                  
                  _buildVerifyField('Adhar no: *', _aadharController, 'upload adhar card'),
                  const SizedBox(height: 20),
                  _buildVerifyField('Pan card no(Ngo/Admin): *', _panController, 'upload pan card'),
                  const SizedBox(height: 20),
                  _buildUploadOnlyField('Ngo registration certificate upload *', isCompulsory: true),
                  
                  if (widget.tier == 2) ...[
                    const SizedBox(height: 20),
                    _buildUploadOnlyField('UPLOAD 12 A Certificate *', isCompulsory: true),
                    const SizedBox(height: 20),
                    _buildUploadOnlyField('Upload 80G Certificate', isOptional: true),
                  ],
                  
                  const SizedBox(height: 48),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Previous', style: TextStyle(color: Colors.grey)),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(minimumSize: const Size(120, 50)),
                        onPressed: _onVerify,
                        child: const Text('Verify'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          _buildProgressDots(2),
        ],
      ),
    );
  }

  Widget _buildVerifyField(String label, TextEditingController controller, String uploadText) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const Icon(Icons.info_outline_rounded, size: 16, color: Colors.grey),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: const InputDecoration(hintText: 'Enter number'),
        ),
        const SizedBox(height: 8),
        const Text('OR', style: TextStyle(fontSize: 10, color: Colors.grey), textAlign: TextAlign.center),
        const SizedBox(height: 8),
        _buildUploadButton(uploadText),
      ],
    );
  }

  Widget _buildUploadOnlyField(String label, {bool isCompulsory = false, bool isOptional = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const Icon(Icons.info_outline_rounded, size: 16, color: Colors.grey),
          ],
        ),
        if (isCompulsory) const Text('* compulsory', style: TextStyle(color: Colors.red, fontSize: 10)),
        if (isOptional) const Text('(optional)', style: TextStyle(color: Colors.grey, fontSize: 10)),
        const SizedBox(height: 12),
        _buildUploadButton('Upload Document'),
      ],
    );
  }

  Widget _buildUploadButton(String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppTheme.borderRadius),
        border: Border.all(color: AppTheme.tealPrimary.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.file_upload_outlined, size: 18, color: AppTheme.tealPrimary),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(color: AppTheme.tealPrimary, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildProgressDots(int currentIndex) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(4, (index) {
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

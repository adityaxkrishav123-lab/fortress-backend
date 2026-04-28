import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/services/api_service.dart';
import 'package:fortress_mobile/screens/dashboard/dashboard_screen.dart';

class VolunteerSignupScreen extends StatefulWidget {
  const VolunteerSignupScreen({super.key});

  @override
  State<VolunteerSignupScreen> createState() => _VolunteerSignupScreenState();
}

class _VolunteerSignupScreenState extends State<VolunteerSignupScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _aadharController = TextEditingController();
  final _pinController = TextEditingController();
  final _confirmPinController = TextEditingController();
  String? _selectedRegion;
  String? _selectedProfession;
  bool _isLoading = false;

  // Placeholder lists from backend logic
  final List<String> _regions = [
    'MUMBAI', 'PUNE', 'NASHIK', 'THANE', 'RAIGAD', 'AURANGABAD', 'KOLHAPUR', 'SOLAPUR', 'NAGPUR', 'AMRAVATI',
    'DELHI', 'GURGAON', 'NOIDA', 'BANGALORE', 'CHENNAI', 'HYDERABAD', 'AHMEDABAD', 'SURAT'
  ];

  final List<String> _professions = [
    'Doctor', 'Nurse', 'Paramedic', 'Blood Donor', 'Pharmacist',
    'Engineer', 'Electrician', 'Plumber', 'IT Support',
    'Firefighter', 'Rescue Operative',
    'Cook', 'Teacher', 'Social Worker'
  ];

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _aadharController.dispose();
    _pinController.dispose();
    _confirmPinController.dispose();
    super.dispose();
  }

  Future<void> _onSubmit() async {
    if (_nameController.text.isEmpty || 
        _phoneController.text.isEmpty || 
        _emailController.text.isEmpty || 
        _selectedProfession == null ||
        _aadharController.text.isEmpty || 
        _selectedRegion == null ||
        _pinController.text.length < 6 ||
        _pinController.text != _confirmPinController.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill all mandatory fields and ensure PINs match.'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() { _isLoading = true; });

    try {
      // 1. Generate a dummy UID for the demo flow
      final String dummyUid = 'UID-${_phoneController.text}';

      // 2. Call Volunteer Signup API
      await ApiService.signupVolunteer({
        'uid': dummyUid,
        'name': _nameController.text,
        'email': _emailController.text,
        'phone': '+91${_phoneController.text}',
        'region': _selectedRegion,
        'profession': _selectedProfession,
        'volunteer_type': 'GENERAL', // Default for demo
        'adhar_no': _aadharController.text,
      });

      // 3. Set the Secure PIN
      await ApiService.setupPIN(dummyUid, _pinController.text);

      if (!mounted) return;
      
      // 4. Navigate to Dashboard
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (context) => DashboardScreen(
          role: 'VOLUNTEER',
          userName: _nameController.text,
        )),
        (route) => false,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() { _isLoading = false; });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Signup Failed: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Volunteer Identification'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppTheme.navySecondary),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Signup as Volunteer', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primaryColor)),
            const SizedBox(height: 8),
            const Text('* all fields are mandatory', style: TextStyle(color: Colors.redAccent, fontSize: 12)),
            const SizedBox(height: 24),
            
            _buildTextField('Name', _nameController, Icons.person_outline_rounded),
            const SizedBox(height: 16),
            _buildPhoneField('Contact no', _phoneController, Icons.phone_android_rounded),
            const SizedBox(height: 16),
            _buildTextField('Email', _emailController, Icons.email_outlined),
            const SizedBox(height: 16),
            _buildSearchableRegion(),
            const SizedBox(height: 16),
            _buildProfessionDropdown(),
            const SizedBox(height: 16),
            _buildVerifyField('Adhar no:', _aadharController, 'upload adhar card'),
            
            const SizedBox(height: 32),
            const Divider(color: Colors.white10),
            const SizedBox(height: 32),
            
            const Text('Security Setup', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryColor)),
            const SizedBox(height: 16),
            const Text('Set 6 digit pin *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            _buildPinField(_pinController),
            const SizedBox(height: 16),
            const Text('Confirm pin *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            _buildPinField(_confirmPinController),
            
            const SizedBox(height: 48),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Previous', style: TextStyle(color: Colors.white54)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(120, 50),
                    backgroundColor: AppTheme.primaryColor,
                    foregroundColor: Colors.black,
                  ),
                  onPressed: _onSubmit,
                  child: const Text('Submit'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }


  Widget _buildTextField(String label, TextEditingController controller, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
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

  Widget _buildPhoneField(String label, TextEditingController controller, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            prefixIcon: Icon(icon, color: AppTheme.tealPrimary),
            prefixText: '+91 ',
            hintText: '10-digit number',
          ),
        ),
      ],
    );
  }

  Widget _buildSearchableRegion() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Text('Region', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        Autocomplete<String>(
          optionsBuilder: (TextEditingValue textEditingValue) {
            if (textEditingValue.text == '') {
              return const Iterable<String>.empty();
            }
            return _regions.where((String option) {
              return option.contains(textEditingValue.text.toUpperCase());
            });
          },
          onSelected: (String selection) {
            setState(() => _selectedRegion = selection);
          },
          fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
            return TextField(
              controller: controller,
              focusNode: focusNode,
              onEditingComplete: onFieldSubmitted,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.location_on_outlined, color: AppTheme.tealPrimary),
                hintText: 'Search & Select Region',
                suffixIcon: Icon(Icons.search_rounded, size: 20, color: Colors.grey),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildProfessionDropdown() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Text('Specialized Skill / Profession', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppTheme.borderRadius),
            border: Border.all(color: Colors.grey.withOpacity(0.2)),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _selectedProfession,
              isExpanded: true,
              hint: const Text('Select Profession'),
              items: _professions.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
              onChanged: (val) => setState(() => _selectedProfession = val),
            ),
          ),
        ),
      ],
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
            const Text(' *', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: const InputDecoration(hintText: 'Enter number'),
        ),
        const SizedBox(height: 12),
        Container(
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
              Text(uploadText, style: const TextStyle(color: AppTheme.tealPrimary, fontSize: 13)),
            ],
          ),
        ),
      ],
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
}

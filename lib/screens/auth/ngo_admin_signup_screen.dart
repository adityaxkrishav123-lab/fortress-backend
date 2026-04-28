import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/auth/ngo_admin_signup/tier_selection_screen.dart';

class NGOAdminSignupScreen extends StatefulWidget {
  const NGOAdminSignupScreen({super.key});

  @override
  State<NGOAdminSignupScreen> createState() => _NGOAdminSignupScreenState();
}

class _NGOAdminSignupScreenState extends State<NGOAdminSignupScreen> {
  final _nameController = TextEditingController();
  final _contactController = TextEditingController();
  final _emailController = TextEditingController();
  final _ngoMailController = TextEditingController();
  final _ngoContactController = TextEditingController();
  final _ngoNameController = TextEditingController();
  String? _selectedRegion;

  // Placeholder list - in production this would be fetched from Nodepoints
  final List<String> _regions = [
    'MUMBAI', 'PUNE', 'NASHIK', 'THANE', 'RAIGAD', 'AURANGABAD', 'KOLHAPUR', 'SOLAPUR', 'NAGPUR', 'AMRAVATI',
    'DELHI', 'GURGAON', 'NOIDA', 'BANGALORE', 'CHENNAI', 'HYDERABAD', 'AHMEDABAD', 'SURAT'
  ];

  @override
  void dispose() {
    _nameController.dispose();
    _contactController.dispose();
    _emailController.dispose();
    _ngoMailController.dispose();
    _ngoContactController.dispose();
    _ngoNameController.dispose();
    super.dispose();
  }

  void _onNext() {
    if (_nameController.text.isEmpty || 
        _contactController.text.isEmpty || 
        _emailController.text.isEmpty || 
        _ngoMailController.text.isEmpty || 
        _ngoContactController.text.isEmpty || 
        _ngoNameController.text.isEmpty || 
        _selectedRegion == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All fields are mandatory!'), backgroundColor: Colors.red),
      );
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(builder: (context) => const TierSelectionScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sign up as Ngo admin'),
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
                  const Text('Sign up form', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
                  const SizedBox(height: 8),
                  const Text('* all fields are mandatory', style: TextStyle(color: Colors.red, fontSize: 12)),
                  const SizedBox(height: 24),
                  
                  _buildTextField('Name', _nameController, Icons.person_outline_rounded, isMandatory: true),
                  const SizedBox(height: 16),
                  
                  _buildPhoneField('Contact no', _contactController, Icons.phone_android_rounded),
                  const SizedBox(height: 16),
                  
                  _buildTextField('Email', _emailController, Icons.email_outlined, isMandatory: true),
                  const SizedBox(height: 16),
                  _buildTextField('Ngo mail', _ngoMailController, Icons.mail_outline_rounded, isMandatory: true),
                  const SizedBox(height: 16),
                  
                  _buildPhoneField('Ngo contact', _ngoContactController, Icons.phone_in_talk_rounded),
                  const SizedBox(height: 16),
                  
                  _buildTextField('Ngo Name', _ngoNameController, Icons.business_rounded, isMandatory: true),
                  const SizedBox(height: 16),
                  
                  _buildSearchableRegion(),
                  
                  const SizedBox(height: 48),
                  ElevatedButton(
                    onPressed: _onNext,
                    child: const Text('Next'),
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

  Widget _buildSearchableRegion() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Text('Region (Ngo)', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
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
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.location_on_outlined, color: AppTheme.tealPrimary),
                hintText: 'Search & Select Region',
                suffixIcon: const Icon(Icons.search_rounded, size: 20, color: Colors.grey),
              ),
            );
          },
          optionsViewBuilder: (context, onSelected, options) {
            return Align(
              alignment: Alignment.topLeft,
              child: Material(
                elevation: 4,
                borderRadius: BorderRadius.circular(AppTheme.borderRadius),
                child: Container(
                  width: MediaQuery.of(context).size.width - 48,
                  constraints: const BoxConstraints(maxHeight: 200),
                  child: ListView.builder(
                    padding: EdgeInsets.zero,
                    shrinkWrap: true,
                    itemCount: options.length,
                    itemBuilder: (BuildContext context, int index) {
                      final String option = options.elementAt(index);
                      return ListTile(
                        title: Text(option),
                        onTap: () => onSelected(option),
                      );
                    },
                  ),
                ),
              ),
            );
          },
        ),
      ],
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

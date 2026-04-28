import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';

class ProfileScreen extends StatefulWidget {
  final String role;
  final String userName;
  final String? rank;

  const ProfileScreen({
    super.key,
    required this.role,
    required this.userName,
    this.rank,
  });

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  // Mock User Data
  late TextEditingController _nameController;
  late TextEditingController _emailController;
  late TextEditingController _phoneController;
  late TextEditingController _ngoEmailController;
  late TextEditingController _ngoPhoneController;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.userName);
    _emailController = TextEditingController(text: 'commander@example.com');
    _phoneController = TextEditingController(text: '+91 98821-XXXXX');
    _ngoEmailController = TextEditingController(text: 'ops@fortress-ngo.org');
    _ngoPhoneController = TextEditingController(text: '022-8821-4400');
  }

  @override
  Widget build(BuildContext context) {
    bool isAdmin = widget.role == 'NGO_ADMIN';

    return Scaffold(
      backgroundColor: Colors.white,
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: Column(
          children: [
            _buildProfileHeader(),
            const SizedBox(height: 40),
            
            // Personal Details Section
            _sectionHeader('PERSONAL IDENTITY'),
            const SizedBox(height: 16),
            _buildField(label: 'Full Name', controller: _nameController, isEditable: true),
            _buildField(label: 'Personal Email', controller: _emailController, isEditable: true),
            _buildField(label: 'Phone Number', controller: _phoneController, isEditable: true),
            
            const SizedBox(height: 32),
            
            // Operational Details Section
            _sectionHeader('NGO OPERATIONS'),
            const SizedBox(height: 16),
            _buildField(label: 'Assigned Rank', controller: TextEditingController(text: widget.rank ?? widget.role), isEditable: false),
            _buildField(label: 'NGO Registry ID', controller: TextEditingController(text: 'REG-NGO-9921-X'), isEditable: false),
            
            if (isAdmin) ...[
              _buildField(label: 'NGO Contact Email', controller: _ngoEmailController, isEditable: true),
              _buildField(label: 'NGO Office Line', controller: _ngoPhoneController, isEditable: true),
            ],
            
            const SizedBox(height: 48),
            _buildSaveButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileHeader() {
    return Column(
      children: [
        Stack(
          alignment: Alignment.bottomRight,
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(color: AppTheme.tealPrimary, shape: BoxShape.circle),
              child: const CircleAvatar(
                radius: 60,
                backgroundColor: AppTheme.backgroundGray,
                child: Icon(Icons.person_rounded, size: 60, color: AppTheme.navySecondary),
              ),
            ),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle, boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 10)]),
              child: const Icon(Icons.edit_rounded, size: 18, color: AppTheme.tealPrimary),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(widget.userName, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: AppTheme.navySecondary)),
        Text(widget.rank ?? widget.role, style: const TextStyle(color: AppTheme.tealPrimary, fontWeight: FontWeight.bold, letterSpacing: 1)),
      ],
    );
  }

  Widget _sectionHeader(String title) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        title,
        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 2, color: Colors.grey),
      ),
    );
  }

  Widget _buildField({required String label, required TextEditingController controller, required bool isEditable}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            readOnly: !isEditable,
            style: TextStyle(
              fontSize: 15,
              fontWeight: isEditable ? FontWeight.bold : FontWeight.w500,
              color: isEditable ? AppTheme.navySecondary : Colors.grey,
            ),
            decoration: InputDecoration(
              filled: true,
              fillColor: isEditable ? Colors.white : AppTheme.backgroundGray,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              // THE "EDIT BOX" RULE: Border only if isEditable is true
              enabledBorder: isEditable 
                ? OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300, width: 1.5))
                : OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              focusedBorder: isEditable 
                ? OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppTheme.tealPrimary, width: 2))
                : OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSaveButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Profile Synchronized Successfully'), backgroundColor: AppTheme.tealPrimary),
          );
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.navySecondary,
          padding: const EdgeInsets.symmetric(vertical: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          elevation: 8,
          shadowColor: AppTheme.navySecondary.withOpacity(0.4),
        ),
        child: const Text('UPDATE IDENTITY', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, letterSpacing: 1)),
      ),
    );
  }
}

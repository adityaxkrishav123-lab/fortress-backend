import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/auth/login_screen.dart';
import 'package:fortress_mobile/screens/auth/ngo_admin_signup_screen.dart';
import 'package:fortress_mobile/screens/auth/ngo_member_signup_screen.dart';
import 'package:fortress_mobile/screens/auth/citizen_signup_screen.dart';
import 'package:fortress_mobile/screens/auth/volunteer_signup_screen.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),
              Text(
                'Welcome to',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.grey),
              ),
              Text(
                'Fortress',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              const Text(
                'Select your role to begin your identification journey.',
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 40),
              Expanded(
                child: GridView.count(
                  crossAxisCount: 2,
                  mainAxisSpacing: 20,
                  crossAxisSpacing: 20,
                  children: [
                    _buildRoleCard(
                      context, 
                      'NGO Admin', 
                      Icons.admin_panel_settings_rounded,
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (context) => const NGOAdminSignupScreen()),
                      ),
                    ),
                    _buildRoleCard(
                      context, 
                      'NGO Member', 
                      Icons.group_rounded,
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (context) => const NGOMemberSignupScreen()),
                      ),
                    ),
                    _buildRoleCard(
                      context, 
                      'Volunteer', 
                      Icons.volunteer_activism_rounded,
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (context) => const VolunteerSignupScreen()),
                      ),
                    ),
                    _buildRoleCard(
                      context, 
                      'Citizen', 
                      Icons.person_pin_circle_rounded,
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (context) => const CitizenSignupScreen()),
                      ),
                    ),
                  ],
                ),
              ),
              Center(
                child: TextButton(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(builder: (context) => const LoginScreen()),
                    );
                  },
                  child: RichText(
                    text: const TextSpan(
                      text: 'Already have a PIN? ',
                      style: TextStyle(color: Colors.grey),
                      children: [
                        TextSpan(
                          text: 'Login',
                          style: TextStyle(color: AppTheme.tealPrimary, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRoleCard(BuildContext context, String title, IconData icon, {VoidCallback? onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTheme.borderRadius),
      child: Card(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.tealPrimary.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: AppTheme.tealPrimary, size: 32),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
            ),
          ],
        ),
      ),
    );
  }
}

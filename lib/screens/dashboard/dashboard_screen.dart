import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/dashboard/raise_request_page.dart';
import 'package:fortress_mobile/screens/dashboard/mailbox_page.dart';
import 'package:fortress_mobile/screens/dashboard/members_manager_page.dart';
import 'package:fortress_mobile/screens/dashboard/inventory_hub_page.dart';
import 'package:fortress_mobile/screens/dashboard/raise_request_hub_page.dart';

/// Phase 9: NGO Ecosystem Dashboard foundations (Screens 20-22)
/// Includes Identity + Rank, Aesthetic Greeting Hub, and Role-Based Nav.
class DashboardScreen extends StatefulWidget {
  final String role; // 'CITIZEN', 'VOLUNTEER', 'NGO_ADMIN', 'NGO_POWER', 'NGO_MEMBER'
  final String userName;
  final String? rank; // Optional rank for NGO roles

  const DashboardScreen({
    super.key,
    required this.role,
    required this.userName,
    this.rank,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _currentIndex = 0;
  bool _hasUnreadUpdates = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _showPermissionPopup();
      _handleFirstTimeNGOOnboarding();
    });
  }

  void _handleFirstTimeNGOOnboarding() {
    if (widget.role == 'NGO_ADMIN') {
      _showAdminInvitePopup();
    } else if (widget.role == 'NGO_POWER' || widget.role == 'NGO_MEMBER') {
      _showMemberWaitingWindow();
    }
  }

  void _showAdminInvitePopup() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.borderRadius)),
        title: const Text('Welcome Commander', style: TextStyle(color: AppTheme.navySecondary, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Your NGO is active. Share this code to onboard your team:'),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: AppTheme.backgroundGray,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('FORT-NGO-8821', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
                  IconButton(
                    icon: const Icon(Icons.copy_rounded, color: AppTheme.tealPrimary),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Referral code copied!')),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('GET STARTED', style: TextStyle(color: AppTheme.tealPrimary, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showMemberWaitingWindow() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        Future.delayed(const Duration(seconds: 3), () {
          if (Navigator.canPop(context)) Navigator.pop(context);
        });

        return Dialog(
          backgroundColor: Colors.transparent,
          elevation: 0,
          child: Container(
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 60,
                  height: 60,
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation<Color>(AppTheme.tealPrimary),
                    strokeWidth: 6,
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Synchronizing...',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
                ),
                const SizedBox(height: 8),
                Text(
                  'Connecting to NGO Database',
                  style: TextStyle(color: AppTheme.navySecondary.withOpacity(0.5), fontSize: 14),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showPermissionPopup() {
    List<String> permissions = ['Storage', 'Media'];
    if (widget.role == 'CITIZEN') {
      permissions.add('Location (GPS)');
    }

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.borderRadius)),
        title: const Text('Permissions Required', style: TextStyle(color: AppTheme.navySecondary, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('To ensure a secure experience, Fortress requires:'),
            const SizedBox(height: 16),
            ...permissions.map((p) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  const Icon(Icons.check_circle, color: AppTheme.tealPrimary, size: 18),
                  const SizedBox(width: 8),
                  Text(p, style: const TextStyle(fontWeight: FontWeight.w500)),
                ],
              ),
            )),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('ALLOW ALL', style: TextStyle(color: AppTheme.tealPrimary, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundGray,
      body: SafeArea(
        child: Column(
          children: [
            _buildUniversalTopBar(),
            Expanded(
              child: IndexedStack(
                index: _currentIndex,
                children: _buildTabScreens(),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        selectedItemColor: AppTheme.tealPrimary,
        unselectedItemColor: Colors.grey,
        backgroundColor: Colors.white,
        type: BottomNavigationBarType.fixed,
        items: _buildBottomNavItems(),
      ),
    );
  }

  List<Widget> _buildTabScreens() {
    // Shared Mailbox
    final mailbox = MailboxPage(
      onRefreshGlow: () => setState(() => _hasUnreadUpdates = false),
      userRole: widget.role,
    );

    // NGO Specific Pages
    final dashboard = _buildAestheticGreetingHub();
    final inventory = InventoryHubPage(role: widget.role);
    final members   = MembersManagerPage(role: widget.role);
    final raiseHub  = RaiseRequestHubPage(role: widget.role);

    if (widget.role == 'NGO_ADMIN') {
      return [dashboard, inventory, members, raiseHub, mailbox];
    } else if (widget.role == 'NGO_POWER') {
      return [dashboard, inventory, raiseHub, mailbox];
    } else if (widget.role == 'NGO_MEMBER') {
      return [dashboard, inventory, mailbox];
    } else if (widget.role == 'CITIZEN') {
      return [
        _buildMainDashboard(),
        mailbox,
        RaiseRequestPage(onSuccess: () => setState(() => _currentIndex = 0)),
      ];
    } else {
      return [_buildMainDashboard(), mailbox];
    }
  }

  Widget _buildUniversalTopBar() {
    String displayName = widget.userName;
    if (widget.rank != null && widget.role.startsWith('NGO_')) {
      displayName = '${widget.userName} (${widget.rank})';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(color: Colors.black12, blurRadius: 10, offset: Offset(0, 4)),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const SizedBox(width: 48), // Spacer
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(
                  'FORTRESS COMMAND',
                  style: TextStyle(
                    color: AppTheme.navySecondary.withOpacity(0.4),
                    fontSize: 10,
                    letterSpacing: 2,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      widget.userName,
                      style: const TextStyle(
                        color: AppTheme.navySecondary,
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    if (widget.rank != null && widget.role.startsWith('NGO_')) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.tealPrimary.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.tealPrimary.withOpacity(0.2)),
                        ),
                        child: Text(
                          widget.rank!.toUpperCase(),
                          style: const TextStyle(
                            color: AppTheme.tealPrimary,
                            fontSize: 9,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.account_circle, size: 36, color: AppTheme.navySecondary),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => ProfileScreen(
                    role: widget.role,
                    userName: widget.userName,
                    rank: widget.rank,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  List<BottomNavigationBarItem> _buildBottomNavItems() {
    List<BottomNavigationBarItem> items = [];

    if (widget.role == 'NGO_ADMIN') {
      items = [
        const BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dash'),
        const BottomNavigationBarItem(icon: Icon(Icons.inventory_2_rounded), label: 'Inventory'),
        const BottomNavigationBarItem(icon: Icon(Icons.people_alt_rounded), label: 'Team'),
        const BottomNavigationBarItem(icon: Icon(Icons.add_alert_rounded), label: 'Raise'),
        _buildMailboxNavItem(),
      ];
    } else if (widget.role == 'NGO_POWER') {
      items = [
        const BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dash'),
        const BottomNavigationBarItem(icon: Icon(Icons.inventory_2_rounded), label: 'Inventory'),
        const BottomNavigationBarItem(icon: Icon(Icons.add_alert_rounded), label: 'Raise'),
        _buildMailboxNavItem(),
      ];
    } else if (widget.role == 'NGO_MEMBER') {
      items = [
        const BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dash'),
        const BottomNavigationBarItem(icon: Icon(Icons.inventory_2_rounded), label: 'Inventory'),
        _buildMailboxNavItem(),
      ];
    } else {
      // Citizen / Volunteer
      items = [
        const BottomNavigationBarItem(icon: Icon(Icons.home_rounded), label: 'Home'),
        _buildMailboxNavItem(),
      ];
      if (widget.role == 'CITIZEN') {
        items.add(const BottomNavigationBarItem(icon: Icon(Icons.add_circle_outline_rounded), label: 'Raise Request'));
      }
    }

    return items;
  }

  BottomNavigationBarItem _buildMailboxNavItem() {
    return BottomNavigationBarItem(
      icon: Stack(
        children: [
          const Icon(Icons.mail_rounded),
          if (_hasUnreadUpdates)
            Positioned(
              right: 0,
              top: 0,
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0.4, end: 1.0),
                duration: const Duration(seconds: 2),
                curve: Curves.easeInOut,
                builder: (context, value, child) {
                  return Opacity(
                    opacity: value,
                    child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: Colors.red,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: Colors.red.withOpacity(0.3),
                            blurRadius: 4 * value,
                            spreadRadius: 2 * value,
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
        ],
      ),
      label: 'Mailbox',
    );
  }

  Widget _buildAestheticGreetingHub() {
    String roleMessage = "Operational Ready";
    if (widget.role == 'NGO_ADMIN') roleMessage = "Strategic Command Active";
    if (widget.role == 'NGO_POWER') roleMessage = "Dispatch Authority Enabled";
    if (widget.role == 'NGO_MEMBER') roleMessage = "Inventory Monitor Active";

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: const Duration(milliseconds: 1200),
      curve: Curves.easeOutCubic,
      builder: (context, value, child) {
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, 30 * (1 - value)),
            child: Padding(
              padding: const EdgeInsets.all(32.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "Welcome Back,",
                    style: TextStyle(
                      fontSize: 16,
                      color: AppTheme.navySecondary.withOpacity(0.5),
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.userName,
                    style: const TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.navySecondary,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppTheme.tealPrimary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      roleMessage,
                      style: const TextStyle(
                        color: AppTheme.tealPrimary,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  const Spacer(),
                  _buildStatusOverview(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatusOverview() {
    return Row(
      children: [
        _statusCard("Active", "12", Icons.bolt_rounded, Colors.orange),
        const SizedBox(width: 16),
        _statusCard("Resolved", "45", Icons.check_circle_rounded, Colors.green),
      ],
    );
  }

  Widget _statusCard(String label, String count, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 4)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 16),
            Text(count, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
            Text(label, style: TextStyle(fontSize: 12, color: AppTheme.navySecondary.withOpacity(0.5))),
          ],
        ),
      ),
    );
  }

  Widget _buildMainDashboard() {
    String greeting = widget.role == 'VOLUNTEER' 
        ? "Welcome Sir!\nwe are glad for your assistance"
        : "Welcome to the app!\n${widget.userName}!";
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 60.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            greeting,
            style: const TextStyle(
              fontSize: 26,
              color: AppTheme.navySecondary,
              fontWeight: FontWeight.w400,
              height: 1.5,
              fontFamily: 'Roboto',
            ),
          ),
          if (widget.role == 'CITIZEN')
            const Padding(
              padding: EdgeInsets.only(top: 12.0),
              child: Text(
                'Have a Nice Day!!!',
                style: TextStyle(
                  color: AppTheme.tealPrimary,
                  fontWeight: FontWeight.bold,
                  fontSize: 20,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPlaceholderScreen(String title) {
    return Center(
      child: Text(
        '$title Screen',
        style: const TextStyle(fontSize: 18, color: Colors.grey),
      ),
    );
  }
}

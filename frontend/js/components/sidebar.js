
import { logout } from "../auth.js";

const shared = [
  { icon: "◫", label: "Dashboard", active: true },
  { icon: "▤", label: "Browse Library" },
  { icon: "🔔", label: "Notifications" },
  { icon: "⚙", label: "My Profile" },
];

const roleItems = {
  student: [
    { icon: "◷", label: "Reading History" },
    { icon: "☆", label: "My Bookmarks" },
    { icon: "✦", label: "Recommendations" },
    { icon: "✉", label: "Resource Requests" },
  ],
  lecturer: [
    { icon: "▦", label: "Course Reading Lists" },
    { icon: "✦", label: "Recommendations" },
    { icon: "✉", label: "Resource Requests" },
  ],
  librarian: [
    { icon: "▣", label: "Manage Resources" },
    { icon: "▦", label: "Reading Lists" },
    { icon: "✉", label: "Manage Requests" },
    { icon: "▥", label: "Library Analytics" },
  ],
  admin: [
    { icon: "♙", label: "User Management" },
    { icon: "▥", label: "Analytics" },
    { icon: "⚙", label: "System Settings" },
  ],
};

export function renderSidebar(role) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;

  sidebar.replaceChildren();

  const brand = document.createElement("div");
  brand.className = "sidebar-brand";
  brand.innerHTML = `
    <span class="sidebar-logo">UNN</span>
    <span>
      <strong>UNN E-Library</strong>
      <small>Academic Resource Portal</small>
    </span>
  `;

  sidebar.append(brand);

  function section(title, items) {
    const label = document.createElement("p");
    label.className = "nav-label";
    label.textContent = title;
    sidebar.append(label);

    items.forEach((item) => {
      const element = document.createElement(
        item.active ? "a" : "button"
      );

      element.className =
        `nav-item ${item.active ? "active" : "pending"}`;

      if (item.active) {
        element.href = "./index.html";
        element.setAttribute("aria-current", "page");
      } else {
        element.type = "button";
        element.disabled = true;
        element.title = "Coming in the next development batch";
      }

      const icon = document.createElement("span");
      icon.textContent = item.icon;

      const text = document.createElement("span");
      text.textContent = item.label;

      element.append(icon, text);
      sidebar.append(element);
    });
  }

  section("MAIN MENU", shared);
  section("YOUR WORKSPACE", roleItems[role] || []);

  const footer = document.createElement("div");
  footer.className = "sidebar-footer";

  const logoutButton = document.createElement("button");
  logoutButton.className = "nav-item logout";
  logoutButton.type = "button";
  logoutButton.textContent = "↪  Log Out";
  logoutButton.addEventListener("click", logout);

  footer.append(logoutButton);
  sidebar.append(footer);
}

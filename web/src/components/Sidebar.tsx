import { NavLink } from 'react-router-dom'
import { MessageSquare, FileText, Shield, BarChart3 } from 'lucide-react'

const navItems = [
  {
    path: '/',
    label: 'Chat',
    icon: MessageSquare,
  },
  {
    path: '/documents',
    label: 'Documents',
    icon: FileText,
  },
  {
    path: '/guardrails',
    label: 'Guardrails',
    icon: Shield,
  },
  {
    path: '/stats',
    label: 'Statistics',
    icon: BarChart3,
  },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-white border-r border-warm-200 flex flex-col z-40">
      <div className="h-16 flex items-center px-6 border-b border-warm-200">
        <span className="text-sm font-semibold text-warm-400 uppercase tracking-wider">
          Navigation
        </span>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-secondary-600 hover:bg-warm-100 hover:text-secondary-900'
              }`
            }
          >
            <item.icon className="w-4.5 h-4.5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-warm-200">
        <div className="bg-warm-50 rounded-lg p-4">
          <p className="text-xs font-medium text-warm-500 uppercase tracking-wider mb-2">
            About
          </p>
          <p className="text-xs text-warm-400 leading-relaxed">
            GuardRAG combines Retrieval-Augmented Generation with multi-layer guardrails to provide secure, trustworthy document Q&A.
          </p>
        </div>
      </div>
    </aside>
  )
}

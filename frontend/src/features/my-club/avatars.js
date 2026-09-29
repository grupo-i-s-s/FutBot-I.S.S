import { Crown, Flame, Rocket, Shield, Star, Zap } from 'lucide-react'

// Biblioteca de avatares provisoria. El backend guarda el avatar como texto;
// estas claves deben acordarse con el formulario de registro.
export const AVATAR_OPTIONS = [
    { key: 'shield', label: 'Escudo', Icon: Shield, className: 'bg-brand text-white' },
    { key: 'flame', label: 'Llama', Icon: Flame, className: 'bg-orange-500 text-white' },
    { key: 'zap', label: 'Rayo', Icon: Zap, className: 'bg-yellow-400 text-ink' },
    { key: 'star', label: 'Estrella', Icon: Star, className: 'bg-sky-600 text-white' },
    { key: 'crown', label: 'Corona', Icon: Crown, className: 'bg-violet-600 text-white' },
    { key: 'rocket', label: 'Cohete', Icon: Rocket, className: 'bg-rose-600 text-white' },
]

export function findAvatar(key) {
    return AVATAR_OPTIONS.find((option) => option.key === key)
}
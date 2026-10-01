import React from 'react';
import BehaviourList from './features/behaviours/components/BehaviourList';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-gray-900">FutBot - Panel</h1>
      </header>
      <main>
        <BehaviourList />
      </main>
    </div>
  );
}

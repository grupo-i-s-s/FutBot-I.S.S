import { Link } from 'react-router';
import {routes} from '@/routes.js';

export default function CancelledLeague() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] p-4 text-center">
            <div className="bg-white-50 border border-black-200 p-6 rounded-xl shadow-md max-w-md w-full">
                <h1 className="text-xl font-bold mb-3">
                    La liga en la que estabas fue cancelada
                </h1>
                <p className="text-sm text-green-600 mb-6">
                    Pero no te preocupes, puedes encontrar otras ligas disponibles
                </p>
                <Link to={routes.leagues} className="inline-block bg-green-600 hover:bg-green-700 text-white font-medium px-5 py-2.5 rounded-lg transition-colors">
                    Ver ligas disponibles
                </Link>
            </div>
        </div>
    );
}
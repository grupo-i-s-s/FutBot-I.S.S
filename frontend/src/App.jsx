import {Navigate, Outlet, Route, Routes} from 'react-router';
import {Button} from '@/components/ui/button';
import HomePage from './features/home-page/homePage.jsx';
import LoginPage from './features/login/LoginPage.jsx';
import RegisterPage from './features/register/RegisterPage.jsx';
import MatchesPage from './features/friendly-matches/Matches.jsx';
import MatchPage from './features/friendly-matches/MatchPage.jsx';
import MyClubPage from './features/my-club/MyClubPage.jsx';
import NotFoundPage from './features/not-found/NotFoundPage.jsx';
import CreateFriendlyMatch from './features/friendly-matches/Create_friendly_match.jsx';
import CreatePlayerPage from './features/create-players/CreatePlayersPage.jsx';
import CrearLiga from './features/crear-liga/CreateLeaguePage.jsx';
import CreatePrivateLeague from './features/crear-liga/CreatePrivateLeaguePage.jsx';
import { LeagueLobby } from './features/lobby-league/CreateLeagueLobby.jsx';
import CancelledLeague from './features/lobby-league/CancelledLeague.jsx';
import ChangePasswordPage from './features/change-password/ChangePasswordPage.jsx';
import InscripcionLigaPage from './features/inscripcion-liga/InscripcionLigaPage.jsx';
import BehaviourDetailPage from './features/behaviours/BehaviourDetailPage.jsx';
import CreateBehaviourPage from './features/create-behaviour/CreateBehaviourPage.jsx';
import BehaviourList from './features/behaviours/components/BehaviourList.jsx';
import LeagueListPage from './features/list-leagues/LeagueListPage.jsx';
import NavBar from './features/nav-bar/navBar.jsx';
import {SessionProvider, useSession} from './features/session/SessionProvider.jsx';
import VerifyEmailPage from './features/register/VerifyEmailPage.jsx';
import ClubsListPage from './features/list-clubs/ClubsListPage.jsx';
import ClubProfilePage from './features/club-profile/ClubProfilePage.jsx';
import LeagueLineupPage from './features/league-lineup/LeagueLineupPage.jsx';

function SessionLoading() {
    return <main className="mx-auto max-w-md px-4 py-8">
        <p role="status">Verificando sesión…</p>
    </main>;
}

function SignIn() {
    const {status} = useSession();
    if (status === 'checking') return <SessionLoading/>;
    return status === 'authenticated' ? <Navigate to="/home" replace/> : <LoginPage/>;
}

function RequireSession() {
    const {status, error, refreshSession} = useSession();
    if (status === 'checking') return <SessionLoading/>;
    if (status === 'anonymous') return <Navigate to="/" replace/>;
    if (status === 'error') {
        return <main className="mx-auto max-w-md space-y-4 px-4 py-8">
            <p role="alert">{error.message}</p>
            <Button onClick={refreshSession}>Reintentar</Button>
        </main>;
    }
    return <Outlet/>;
}

export default function App() {
    return (
        <SessionProvider>
            <NavBar/>
            <Routes>
                <Route path="/" element={<SignIn/>} />
                <Route path="/login" element={<SignIn/>} />
                <Route path="/registro" element={<RegisterPage />} />
                <Route path="/verificar-email" element={<VerifyEmailPage />} />
                <Route element={<RequireSession/>}>
                    <Route path="/home" element={<HomePage />} />
                    <Route path="/mi-club" element={<MyClubPage />} />
                    <Route path="/partidos-disponibles" element={<MatchesPage />} />
                    <Route path="/crear-partido" element={<CreateFriendlyMatch />} />
                    <Route path="/crear-jugador" element={<CreatePlayerPage />} />
                    <Route path="/partidos/:matchId" element={<MatchPage />} />
                    <Route path="/cambiar-contrasena" element={<ChangePasswordPage />} />
                    <Route path="/behaviours/:behaviourId" element={<BehaviourDetailPage />} />
                    <Route path="/ligas-disponibles" element={<LeagueListPage />} />
                    <Route path="/liga-cancelada" element={<CancelledLeague />} />
                    <Route path="/inscripcion-liga" element={<InscripcionLigaPage />} />
                    <Route path="/leagues/:id/join" element={<InscripcionLigaPage />} />
                    <Route path="/crear-liga" element={<CrearLiga />} />
                    <Route path="/crear-liga-privada" element={<CreatePrivateLeague />} />
                    <Route path="/leagues/:id/lobby" element={<LeagueLobby />} />
                    <Route path="/leagues/:id/lineup" element={<LeagueLineupPage />} />
                    <Route path="/behaviours" element={<BehaviourList />} />
                    <Route path="/crear-comportamiento" element={<CreateBehaviourPage />} />
                    <Route path="/crear-comportamiento-dt" element={<CreateBehaviourPage key="dt" kind="DT" />} />
                    <Route path="/clubes" element={<ClubsListPage />} />
                    <Route path="/club/:clubId" element={<ClubProfilePage />} />
                    <Route path="*" element={<NotFoundPage />} />
                </Route>
            </Routes>
        </SessionProvider>
    );
}

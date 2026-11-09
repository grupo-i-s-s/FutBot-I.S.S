import {Navigate, Outlet, Route, Routes, useLocation, useParams, useSearchParams} from 'react-router';
import {Button} from '@/components/ui/button';
import {Toaster} from '@/components/ui/sonner';
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
import GlobalRanking from './features/global-ranking/globalRanking.jsx';
import VerifyEmailPage from './features/register/VerifyEmailPage.jsx';
import PasswordResetPage from './features/password-reset/PasswordResetPage.jsx';
import ClubsListPage from './features/list-clubs/ClubsListPage.jsx';
import ClubProfilePage from './features/club-profile/ClubProfilePage.jsx';
import LeagueLineupPage from './features/league-lineup/LeagueLineupPage.jsx';
import {routePath, routes} from './routes.js';

const privateAliases = [
    ['/home', routes.home],
    ['/behaviours', routes.behaviours],
    ['/behaviours/:behaviourId', routes.behaviourDetail],
    ['/club/:clubId', routes.clubProfile],
    ['/leagues/:id/join', routes.leagueRegistration],
    ['/leagues/:id/lobby', routes.leagueLobby],
    ['/leagues/:id/lineup', routes.leagueLineup],
];

function LegacyRedirect({to}) {
    const {search, hash, state} = useLocation();
    const params = useParams();
    return <Navigate to={{pathname: routePath(to, params), search, hash}} state={state} replace/>;
}

function LegacyLeagueRegistration() {
    const {search, hash, state} = useLocation();
    const [searchParams] = useSearchParams();
    const leagueId = searchParams.get('leagueId');
    if (!leagueId) return <InscripcionLigaPage/>;

    const pathname = routePath(routes.leagueRegistration, {id: leagueId});
    return <Navigate to={{pathname, search, hash}} state={state} replace/>;
}

function SessionLoading() {
    return <main className="mx-auto max-w-md px-4 py-8">
        <p role="status">Verificando sesión…</p>
    </main>;
}

function SignIn() {
    const {status} = useSession();
    const {search, hash, state} = useLocation();
    if (status === 'checking') return <SessionLoading/>;
    if (status === 'authenticated') {
        return <Navigate to={{pathname: routes.home, search, hash}} state={state} replace/>;
    }
    return <LoginPage/>;
}

function RequireSession() {
    const {status, error, refreshSession} = useSession();
    if (status === 'checking') return <SessionLoading/>;
    if (status === 'anonymous') return <Navigate to={routes.root} replace/>;
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
                <Route path={routes.root} element={<SignIn/>} />
                <Route path={routes.signIn} element={<SignIn/>} />
                <Route path={routes.register} element={<RegisterPage />} />
                <Route path={routes.verifyEmail} element={<VerifyEmailPage />} />
                <Route path={routes.passwordReset} element={<PasswordResetPage />} />
                <Route path="/login" element={<LegacyRedirect to={routes.signIn}/>} />
                <Route element={<RequireSession/>}>
                    <Route path={routes.home} element={<HomePage />} />
                    <Route path={routes.myClub} element={<MyClubPage />} />
                    <Route path={routes.friendlyMatches} element={<MatchesPage />} />
                    <Route path={routes.createMatch} element={<CreateFriendlyMatch />} />
                    <Route path={routes.createPlayer} element={<CreatePlayerPage />} />
                    <Route path={routes.match} element={<MatchPage />} />
                    <Route path={routes.changePassword} element={<ChangePasswordPage />} />
                    <Route path={routes.behaviourDetail} element={<BehaviourDetailPage />} />
                    <Route path={routes.leagues} element={<LeagueListPage />} />
                    <Route path={routes.cancelledLeague} element={<CancelledLeague />} />
                    <Route path={routes.leagueRegistration} element={<InscripcionLigaPage />} />
                    <Route path={routes.createLeague} element={<CrearLiga />} />
                    <Route path={routes.createPrivateLeague} element={<CreatePrivateLeague />} />
                    <Route path={routes.leagueLobby} element={<LeagueLobby />} />
                    <Route path={routes.leagueLineup} element={<LeagueLineupPage />} />
                    <Route path={routes.behaviours} element={<BehaviourList />} />
                    <Route path={routes.createBehaviour} element={<CreateBehaviourPage />} />
                    <Route path={routes.createDtBehaviour} element={<CreateBehaviourPage key="dt" kind="DT" />} />
                    <Route path={routes.clubs} element={<ClubsListPage />} />
                    <Route path={routes.clubProfile} element={<ClubProfilePage />} />
                    <Route path={routes.globalRanking} element={<GlobalRanking />} />
                    <Route path="/inscripcion-liga" element={<LegacyLeagueRegistration/>} />
                    {privateAliases.map(([path, to]) => (
                        <Route key={path} path={path} element={<LegacyRedirect to={to}/>} />
                    ))}
                    <Route path="*" element={<NotFoundPage />} />
                </Route>
            </Routes>
            <Toaster
                position="bottom-right"
                offset={16}
                duration={5000}
                visibleToasts={1}
                closeButton
                containerAriaLabel="Notificaciones"
                toastOptions={{closeButtonAriaLabel: 'Cerrar notificación'}}
            />
        </SessionProvider>
    );
}

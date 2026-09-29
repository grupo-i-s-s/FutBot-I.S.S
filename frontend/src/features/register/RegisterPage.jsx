
import './RegisterPage.css'

export default function RegisterPage() {
    return (
        <main className="register-page">
            <h1 className="main-page-title">¡Bienvenido a FutBot!</h1>
                <section className="user_register-card">
                    <h1 className="register-title">Registro Usuario</h1>
                    <form>
                        <div className="formulary-box">
                            <label htmlFor="user-name">Nombre de Usuario</label>
                            <input id="user-name" type="text" placeholder="Tu nombre" />
                        </div>
                        <div className="formulary-box">
                            <label htmlFor="club-name">Nombre del Club</label>
                            <input id="club-name" type="text" placeholder="Nombre del club" />
                        </div>

                        <div className="formulary-box">
                            <label htmlFor="avatar">Avatar</label>
                            <input id="avatar" type="text" placeholder="" />
                        </div>

                        <div className="formulary-box">
                            <label htmlFor="user-email">Email</label>
                            <input id="user-email" type="email" placeholder="i.e: PepeArgento@gmail.com" />
                        </div>

                        <div className="formulary-box">
                            <label htmlFor="user-password">Contraseña</label>
                            <input id="user-password" type="password" placeholder="Tu contraseña" />
                        </div>

                        <div className = "formulary-box">
                            <label htmlFor="user-password-confirm">Confirmar Contraseña</label>
                            <input id="user-password-confirm" type="password" placeholder="Repita la constraeña" />
                        </div>
                    </form>
                    <form>
                        <button type="button" className="register-button">
                            Registrar Club
                        </button>
                    </form>
                </section>
        </main>
    )
}
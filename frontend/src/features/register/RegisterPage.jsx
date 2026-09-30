
import './RegisterPage.css'
import { useState } from 'react'
import { register } from './api'

export default function RegisterPage() {

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const[repeatPassword, setRepeatPassword] = useState('')
    const[avatar, setAvatar]  = useState('')
    const[clubName, setClubName] = useState('')
    const[userName, setUserName] = useState('')
    const [name, setName] = useState();

    
    async function handleSubmit(event) {
        event.preventDefault()
        const response = await register(name, userName, email, clubName, password, repeatPassword, avatar)
        console.log(response)
        console.log(response.status)
    }


    return (
        <main className="register-page">
            <h1 className="main-page-title">¡Bienvenido a FutBot!</h1>
                <section className="user_register-card">
                    <h1 className="register-title">Registro Usuario</h1>
                    <form onSubmit={handleSubmit}> 
                        <div className="formulary-box">
                            <label htmlFor="name">Nombre</label>
                            <input  
                                    id="user-name" 
                                    type="text" 
                                    placeholder="Tu nombre" 
                                    value = {name}
                                    onChange = {(event) => setName(event.target.value)}>
                            </input>
                        </div>
                        <div className="formulary-box">
                            <label htmlFor="user-name">Nombre de Usuario</label>
                            <input
                                id="user-name"
                                type="text"
                                placeholder="Nombre de usuario"
                                value = {userName}
                                onChange = {(event) => setUserName(event.target.value)}>
                            </input>
                        </div>
                        <div className="formulary-box">
                            <label htmlFor="club-name">Nombre del Club</label>
                                   <input  
                                    id="club-name" 
                                    type="text" 
                                    placeholder="Nombre del club" 
                                    value = {clubName} 
                                    onChange = {(event) => setClubName(event.target.value)}>
                            </input>
                        </div>

                        <div className="formulary-box">
                            <label htmlFor="avatar">Avatar</label>
                            <input  
                                id="Avatar" 
                                type="text" 
                                placeholder="avatar" 
                                value = {avatar} 
                                onChange = {(event) => setAvatar(event.target.value)}>
                            </input>
                        </div>

                        <div className="formulary-box">
                            <label htmlFor="user-email">Email</label>
                            <input  
                                id="user-email" 
                                type="email" 
                                placeholder="pepeArgento@gmail.com" 
                                value = {email} 
                                onChange = {(event) => setEmail(event.target.value)}>
                        </input>
                        </div>

                        <div className="formulary-box">
                            <label htmlFor="user-password">Contraseña</label>
                            <input  
                                id="password" 
                                type="password" 
                                placeholder="Contraseña" 
                                value = {password} 
                                onChange = {(event) => setPassword(event.target.value)}>
                            </input>
                        </div>

                        <div className = "formulary-box">
                            <label htmlFor="user-password-confirm">Confirmar Contraseña</label>
                            <input  
                                id="password" 
                                type="password" 
                                placeholder="Confimar-contraseña" 
                                value = {repeatPassword} 
                                onChange = {(event) => setRepeatPassword(event.target.value)}>
                            </input>
                        </div>
                        <button type="submit" className="register-button">
                            Registrar Club
                        </button>
                    </form>
                </section>
        </main>
    )
}
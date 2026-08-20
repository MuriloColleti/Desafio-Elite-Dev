import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ProvedorSessao } from './auth/Sessao'
import { Layout } from './componentes/Layout'
import { Protegida } from './componentes/Protegida'
import { Checkout } from './telas/Checkout'
import { CriarConta } from './telas/CriarConta'
import { DetalheEvento } from './telas/DetalheEvento'
import { Entrar } from './telas/Entrar'
import { IngressoPublico } from './telas/IngressoPublico'
import { MeusIngressos } from './telas/MeusIngressos'
import { NovoEvento } from './telas/NovoEvento'
import { PainelOrganizador } from './telas/PainelOrganizador'
import { Portaria } from './telas/Portaria'
import { Vitrine } from './telas/Vitrine'

export default function App() {
  return (
    <ProvedorSessao>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            {/* Público. A vitrine tem duas abas e a escolhida vive na URL,
                então o link de uma aba é compartilhável. */}
            <Route path="/" element={<Vitrine />} />
            <Route path="/shows" element={<Vitrine />} />
            <Route path="/cinema" element={<Vitrine />} />
            <Route path="/eventos/:id" element={<DetalheEvento />} />
            <Route path="/entrar" element={<Entrar />} />
            <Route path="/criar-conta" element={<CriarConta />} />
            {/* Link de compartilhamento: curto de propósito, é feito para ser
                colado em conversa. */}
            <Route path="/i/:token" element={<IngressoPublico />} />

            {/* Cliente */}
            <Route
              path="/checkout/:reservaId"
              element={
                <Protegida papel="CUSTOMER">
                  <Checkout />
                </Protegida>
              }
            />
            <Route
              path="/meus-ingressos"
              element={
                <Protegida papel="CUSTOMER">
                  <MeusIngressos />
                </Protegida>
              }
            />
            {/* O checkout redireciona para cá após pagar; a lista já mostra o
                ingresso novo, então não há tela separada de "sucesso". */}
            <Route path="/ingresso/:id" element={<Navigate to="/meus-ingressos" replace />} />

            {/* Organizador */}
            <Route
              path="/organizador"
              element={
                <Protegida papel="ORGANIZER">
                  <PainelOrganizador />
                </Protegida>
              }
            />
            <Route
              path="/organizador/novo"
              element={
                <Protegida papel="ORGANIZER">
                  <NovoEvento />
                </Protegida>
              }
            />

            {/* Portaria */}
            <Route
              path="/portaria"
              element={
                <Protegida papel="GATE">
                  <Portaria />
                </Protegida>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProvedorSessao>
  )
}

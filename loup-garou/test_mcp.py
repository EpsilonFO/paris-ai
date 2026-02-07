#!/usr/bin/env python3
"""
Script de test pour le serveur MCP Loup-Garou
Joue une partie complète jusqu'à la victoire
Usage: python test_mcp.py
"""
import asyncio
import json
import random
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def print_header(text: str, emoji: str = ""):
    print(f"\n{'='*60}")
    print(f"{emoji} {text}")
    print("="*60)


def print_event(text: str):
    print(f"  → {text}")


async def play_full_game():
    """Joue une partie complète via MCP"""

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp_server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ============================================
            # CRÉATION DE LA PARTIE
            # ============================================
            print_header("CRÉATION DE LA PARTIE", "🎮")

            result = await session.call_tool("create_game", {
                "player_name": "Joueur",
                "num_players": 6,
                "num_wolves": 2
            })

            game_data = json.loads(result.content[0].text)
            game_id = game_data["game_id"]
            my_role = game_data["your_role"]
            my_faction = game_data["your_faction"]

            print_event(f"Partie créée: {game_id}")
            print_event(f"Votre rôle: {my_role} ({my_faction})")
            print_event(f"Joueurs: Vous + {len(game_data['players'])} IA")

            if "fellow_wolves" in game_data:
                print_event(f"Vos alliés loups: {', '.join(game_data['fellow_wolves'])}")

            for p in game_data["players"]:
                print(f"     - {p['name']}: {p['personality']}")

            # ============================================
            # BOUCLE DE JEU
            # ============================================
            turn = 0
            game_over = False

            while not game_over:
                turn += 1

                # Obtenir l'état actuel
                result = await session.call_tool("get_game_state", {"game_id": game_id})
                state = json.loads(result.content[0].text)

                if state.get("status") != "en_cours":
                    game_over = True
                    break

                day_number = state["day_number"]
                phase = state["phase"]
                alive = [p["name"] for p in state["alive_players"]]
                i_am_alive = state["you_are_alive"]

                # ============================================
                # PHASE DE NUIT
                # ============================================
                if phase == "nuit":
                    print_header(f"NUIT {day_number}", "🌙")
                    print_event(f"Joueurs en vie: {', '.join(alive)}")

                    if not i_am_alive:
                        print_event("Vous êtes mort. Vous observez depuis l'au-delà...")
                        # Passer la nuit automatiquement
                        result = await session.call_tool("skip_night", {"game_id": game_id})
                    else:
                        # Trouver les cibles possibles (pas soi-même)
                        targets = [p["name"] for p in state["alive_players"] if not p["is_you"]]

                        if my_role == "Loup-Garou":
                            # Choisir une victime au hasard parmi les non-loups
                            target = random.choice(targets)
                            print_event(f"🐺 Vous attaquez {target}...")
                            result = await session.call_tool("wolf_attack", {
                                "game_id": game_id,
                                "target": target
                            })

                        elif my_role == "Voyante":
                            target = random.choice(targets)
                            print_event(f"🔮 Vous observez {target}...")
                            result = await session.call_tool("seer_observe", {
                                "game_id": game_id,
                                "target": target
                            })
                            action_result = json.loads(result.content[0].text)
                            if "seer_result" in action_result:
                                sr = action_result["seer_result"]
                                wolf_emoji = "🐺" if sr["is_wolf"] else "🏠"
                                print_event(f"Vision: {sr['target']} est {sr['role']} {wolf_emoji}")

                        elif my_role == "Sorcière":
                            # Stratégie simple: sauver au premier tour, tuer si suspect
                            use_life = state.get("potions", {}).get("life", False) and day_number == 1
                            kill_target = None

                            if state.get("potions", {}).get("death", False) and day_number > 2:
                                kill_target = random.choice(targets)

                            print_event(f"🧪 Sorcière: vie={use_life}, mort={kill_target}")
                            result = await session.call_tool("witch_action", {
                                "game_id": game_id,
                                "use_life_potion": use_life,
                                "kill_target": kill_target
                            })

                        else:  # Villageois
                            print_event("😴 Vous dormez paisiblement...")
                            result = await session.call_tool("skip_night", {"game_id": game_id})

                    # Analyser le résultat de la nuit
                    action_result = json.loads(result.content[0].text)

                    if "night_events" in action_result:
                        events = action_result["night_events"]
                        if events.get("saved"):
                            print_event(f"✨ {events['saved']} a été sauvé(e) par la sorcière!")
                        for death in events.get("deaths", []):
                            print_event(f"💀 {death['name']} ({death['role']}) est mort(e) - {death['cause']}")
                        if not events.get("deaths") and not events.get("saved"):
                            print_event("Nuit calme, personne n'est mort.")

                    if "game_over" in action_result:
                        game_over = True
                        winner = action_result["game_over"]["winner"]
                        print_header(f"VICTOIRE: {winner}", "🏆")
                        break

                # ============================================
                # PHASE DE JOUR
                # ============================================
                # Rafraîchir l'état après la nuit
                result = await session.call_tool("get_game_state", {"game_id": game_id})
                state = json.loads(result.content[0].text)

                if state.get("status") != "en_cours":
                    game_over = True
                    break

                if state["phase"] == "jour":
                    print_header(f"JOUR {state['day_number']}", "☀️")

                    alive = [p["name"] for p in state["alive_players"]]
                    print_event(f"Survivants: {', '.join(alive)}")

                    # Discussions
                    result = await session.call_tool("get_discussions", {"game_id": game_id})
                    discussions = json.loads(result.content[0].text)

                    print("\n  📢 Discussions:")
                    for disc in discussions.get("discussions", []):
                        print(f"     {disc['player']}: \"{disc['message']}\"")

                    # Vote
                    i_am_alive = state["you_are_alive"]
                    targets = [p["name"] for p in state["alive_players"] if not p["is_you"]]

                    if i_am_alive and targets:
                        # Stratégie de vote selon le rôle
                        if my_role == "Loup-Garou":
                            # Ne pas voter contre un loup (info qu'on a)
                            vote_target = random.choice(targets)
                        else:
                            vote_target = random.choice(targets)

                        print_event(f"🗳️ Vous votez contre {vote_target}")
                    else:
                        vote_target = targets[0] if targets else None
                        print_event(f"🗳️ Vote automatique: {vote_target}")

                    if vote_target:
                        result = await session.call_tool("vote", {
                            "game_id": game_id,
                            "target": vote_target
                        })
                        vote_result = json.loads(result.content[0].text)

                        # Afficher les votes
                        if "votes" in vote_result:
                            print("\n  📊 Résultats du vote:")
                            for voter, voted in vote_result["votes"].items():
                                print(f"     {voter} → {voted}")

                        if "eliminated" in vote_result:
                            elim = vote_result["eliminated"]
                            print_event(f"⚖️ {elim['name']} éliminé(e) ({elim['votes']} votes) - C'était: {elim['role']}")
                        elif vote_result.get("tie"):
                            print_event("⚖️ Égalité! Personne n'est éliminé.")

                        if "game_over" in vote_result:
                            game_over = True
                            winner = vote_result["game_over"]["winner"]
                            print_header(f"VICTOIRE: {winner}", "🏆")
                            break

                # Sécurité anti-boucle infinie
                if turn > 20:
                    print_event("⚠️ Trop de tours, arrêt forcé")
                    break

            # ============================================
            # RÉCAPITULATIF FINAL
            # ============================================
            print_header("FIN DE PARTIE", "🎭")

            result = await session.call_tool("get_game_state", {"game_id": game_id})
            final_state = json.loads(result.content[0].text)

            print(f"  Statut: {final_state['status']}")
            print(f"  Votre rôle était: {my_role} ({my_faction})")

            if final_state["status"] == "victoire_village":
                win = my_faction == "Village"
            else:
                win = my_faction == "Loups-Garous"

            print(f"  {'🎉 VOUS AVEZ GAGNÉ!' if win else '😢 Vous avez perdu...'}")

            print("\n  Morts:")
            for p in final_state.get("dead_players", []):
                print(f"     💀 {p['name']} - {p['role']}")

            print("\n  Survivants:")
            for p in final_state.get("alive_players", []):
                marker = "(vous)" if p["is_you"] else ""
                print(f"     ✅ {p['name']} {marker}")


if __name__ == "__main__":
    asyncio.run(play_full_game())

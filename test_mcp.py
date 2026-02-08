#!/usr/bin/env python3
"""
Script de test interactif pour le serveur MCP Loup-Garou
Joue une partie complète avec interaction humaine
Usage: python test_mcp.py
"""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def print_header(text: str, emoji: str = ""):
    print(f"\n{'='*60}")
    print(f"{emoji} {text}")
    print("="*60)


def print_event(text: str):
    print(f"  → {text}")


def get_choice(options: list[str], prompt: str = "Votre choix") -> str:
    """Demande à l'utilisateur de choisir parmi une liste d'options"""
    print()
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")

    while True:
        try:
            choice = input(f"\n{prompt} (1-{len(options)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, IndexError):
            pass
        print("  ❌ Choix invalide, réessayez.")


def confirm(prompt: str) -> bool:
    """Demande une confirmation oui/non"""
    while True:
        response = input(f"{prompt} (o/n): ").strip().lower()
        if response in ['o', 'oui', 'y', 'yes']:
            return True
        if response in ['n', 'non', 'no']:
            return False
        print("  ❌ Répondez par 'o' ou 'n'")


async def play_interactive_game():
    """Joue une partie interactive via MCP"""

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp_server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ============================================
            # CONFIGURATION DE LA PARTIE
            # ============================================
            print_header("LOUP-GAROU DE THIERCELIEUX", "🐺")
            print("\n  Bienvenue dans le village de Thiercelieux...")
            print("  La nuit, les loups-garous rôdent.")
            print("  Le jour, le village tente de les démasquer.\n")

            player_name = input("  Entrez votre nom: ").strip() or "Joueur"

            print("\n  Configuration de la partie:")
            num_players = input("  Nombre de joueurs (4-8) [6]: ").strip()
            num_players = int(num_players) if num_players.isdigit() else 6
            num_players = max(4, min(8, num_players))

            num_wolves = input("  Nombre de loups (1-3) [2]: ").strip()
            num_wolves = int(num_wolves) if num_wolves.isdigit() else 2
            num_wolves = max(1, min(3, num_wolves))

            # ============================================
            # CRÉATION DE LA PARTIE
            # ============================================
            print_header("LA PARTIE COMMENCE", "🎮")

            result = await session.call_tool("create_game", {
                "player_name": player_name,
                "num_players": num_players,
                "num_wolves": num_wolves
            })

            game_data = json.loads(result.content[0].text)
            game_id = game_data["game_id"]
            my_role = game_data["your_role"]
            my_faction = game_data["your_faction"]

            print(f"\n  {game_data['message']}")
            print(f"\n  🎭 Votre rôle: {my_role}")
            print(f"  🏠 Votre camp: {my_faction}")

            if "fellow_wolves" in game_data:
                wolves = ", ".join(game_data["fellow_wolves"])
                print(f"  🐺 Vos alliés loups: {wolves}")

            print("\n  Les autres habitants du village:")
            for p in game_data["players"]:
                print(f"     • {p['name']}: {p['personality']}")

            input("\n  Appuyez sur Entrée pour commencer...")

            # ============================================
            # BOUCLE DE JEU
            # ============================================
            turn = 0
            game_over = False

            while not game_over:
                turn += 1

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
                    print("\n  Le village s'endort... Les étoiles brillent faiblement.")
                    print(f"  Joueurs en vie: {', '.join(alive)}\n")

                    if not i_am_alive:
                        print("  💀 Vous êtes mort. Vous observez depuis l'au-delà...")
                        input("  Appuyez sur Entrée pour continuer...")
                        result = await session.call_tool("skip_night", {"game_id": game_id})
                    else:
                        targets = [p["name"] for p in state["alive_players"] if not p["is_you"]]

                        if my_role == "Loup-Garou":
                            print("  🐺 Vous vous réveillez avec les autres loups...")
                            if "fellow_wolves" in game_data:
                                print(f"  Vos alliés: {', '.join(game_data['fellow_wolves'])}")
                            print("\n  Qui voulez-vous dévorer cette nuit?")
                            target = get_choice(targets, "Votre victime")
                            print(f"\n  → Vous attaquez {target}...")
                            result = await session.call_tool("wolf_attack", {
                                "game_id": game_id,
                                "target": target
                            })

                        elif my_role == "Voyante":
                            print("  🔮 Vous vous réveillez... Vos visions vous appellent.")
                            print("\n  Qui voulez-vous observer?")
                            target = get_choice(targets, "Observer")
                            result = await session.call_tool("seer_observe", {
                                "game_id": game_id,
                                "target": target
                            })
                            action_result = json.loads(result.content[0].text)
                            if "seer_result" in action_result:
                                sr = action_result["seer_result"]
                                if sr["is_wolf"]:
                                    print(f"\n  🐺 VISION: {sr['target']} est un {sr['role']}!")
                                    print("  Vous avez découvert un loup!")
                                else:
                                    print(f"\n  🏠 VISION: {sr['target']} est {sr['role']}.")
                                    print("  Cette personne semble innocente.")
                            input("\n  Appuyez sur Entrée pour continuer...")

                        elif my_role == "Sorcière":
                            print("  🧪 Vous vous réveillez... Vos potions sont prêtes.")
                            potions = state.get("potions", {})
                            print(f"  Potion de vie: {'✅ disponible' if potions.get('life') else '❌ utilisée'}")
                            print(f"  Potion de mort: {'✅ disponible' if potions.get('death') else '❌ utilisée'}")

                            use_life = False
                            kill_target = None

                            if potions.get("life"):
                                wolf_victim = state.get("wolf_victim")
                                if wolf_victim:
                                    print(f"\n  ⚠️ Les loups ont attaqué {wolf_victim} cette nuit!")
                                    use_life = confirm(f"  Utiliser votre potion de vie pour sauver {wolf_victim}?")
                                else:
                                    print("\n  Les loups n'ont pas encore choisi leur victime.")

                            if potions.get("death"):
                                if confirm("\n  Voulez-vous utiliser votre potion de mort?"):
                                    print("  Qui voulez-vous empoisonner?")
                                    kill_target = get_choice(targets, "Empoisonner")

                            result = await session.call_tool("witch_action", {
                                "game_id": game_id,
                                "use_life_potion": use_life,
                                "kill_target": kill_target
                            })

                            if use_life:
                                print("\n  ✨ Vous versez la potion de vie...")
                            if kill_target:
                                print(f"\n  ☠️ Vous versez la potion de mort sur {kill_target}...")

                        else:  # Villageois
                            print("  😴 Vous êtes un simple villageois.")
                            print("  Vous dormez paisiblement pendant que le danger rôde...")
                            input("\n  Appuyez sur Entrée pour continuer...")
                            result = await session.call_tool("skip_night", {"game_id": game_id})

                    # Résultat de la nuit
                    action_result = json.loads(result.content[0].text)

                    if "night_events" in action_result:
                        events = action_result["night_events"]

                        print_header(f"LEVER DU SOLEIL - JOUR {day_number}", "🌅")

                        if events.get("saved"):
                            print(f"\n  ✨ Miracle! {events['saved']} a survécu à l'attaque!")

                        if events.get("deaths"):
                            for death in events["deaths"]:
                                cause = "dévoré(e) par les loups" if death["cause"] == "loups" else "empoisonné(e)"
                                print(f"\n  💀 {death['name']} a été trouvé(e) mort(e)...")
                                print(f"     C'était un(e) {death['role']}. ({cause})")
                        elif not events.get("saved"):
                            print("\n  ☀️ Miracle! Personne n'est mort cette nuit.")

                        input("\n  Appuyez sur Entrée pour continuer...")

                    if "game_over" in action_result:
                        game_over = True
                        winner = action_result["game_over"]["winner"]
                        print_header(f"VICTOIRE: {winner}", "🏆")
                        break

                # ============================================
                # PHASE DE JOUR
                # ============================================
                result = await session.call_tool("get_game_state", {"game_id": game_id})
                state = json.loads(result.content[0].text)

                if state.get("status") != "en_cours":
                    game_over = True
                    break

                if state["phase"] == "jour":
                    print_header(f"JOUR {state['day_number']} - DISCUSSION", "☀️")

                    alive = [p["name"] for p in state["alive_players"]]
                    print(f"\n  Survivants: {', '.join(alive)}")

                    # Discussions IA
                    result = await session.call_tool("get_discussions", {"game_id": game_id})
                    discussions = json.loads(result.content[0].text)

                    print("\n  📢 Le village débat...\n")
                    for disc in discussions.get("discussions", []):
                        print(f"  💬 {disc['player']}:")
                        print(f"     \"{disc['message']}\"\n")

                    input("  Appuyez sur Entrée pour passer au vote...")

                    # Vote
                    print_header(f"JOUR {state['day_number']} - VOTE", "🗳️")

                    i_am_alive = state["you_are_alive"]
                    targets = [p["name"] for p in state["alive_players"] if not p["is_you"]]

                    if i_am_alive and targets:
                        print("\n  Le village doit désigner un suspect.")
                        print("  Contre qui votez-vous?\n")
                        vote_target = get_choice(targets, "Votre vote")
                        print(f"\n  → Vous votez contre {vote_target}!")
                    elif targets:
                        vote_target = targets[0]
                        print(f"\n  💀 Vous êtes mort, vous ne pouvez pas voter.")
                        print(f"  Le vote continue sans vous...")
                    else:
                        vote_target = None

                    if vote_target:
                        result = await session.call_tool("vote", {
                            "game_id": game_id,
                            "target": vote_target
                        })
                        vote_result = json.loads(result.content[0].text)

                        # Résultats du vote
                        print("\n  📊 Résultats du vote:")
                        if "votes" in vote_result:
                            vote_counts = {}
                            for voter, voted in vote_result["votes"].items():
                                vote_counts[voted] = vote_counts.get(voted, 0) + 1
                                you_marker = " (vous)" if voter == player_name else ""
                                print(f"     {voter}{you_marker} → {voted}")

                            print("\n  Décompte:")
                            for name, count in sorted(vote_counts.items(), key=lambda x: -x[1]):
                                print(f"     {name}: {count} vote(s)")

                        if "eliminated" in vote_result:
                            elim = vote_result["eliminated"]
                            print(f"\n  ⚖️ Le village a décidé!")
                            print(f"  {elim['name']} est éliminé(e) avec {elim['votes']} votes.")
                            print(f"  C'était un(e) {elim['role']}.")

                            if elim["role"] == "Loup-Garou":
                                print("  🎉 Un loup de moins!")
                            else:
                                print("  😢 Un innocent est mort...")
                        elif vote_result.get("tie"):
                            print("\n  ⚖️ Égalité! Le village ne parvient pas à se décider.")
                            print("  Personne n'est éliminé aujourd'hui.")

                        input("\n  Appuyez sur Entrée pour continuer...")

                        if "game_over" in vote_result:
                            game_over = True
                            winner = vote_result["game_over"]["winner"]
                            print_header(f"VICTOIRE: {winner}", "🏆")
                            break

                # Sécurité anti-boucle
                if turn > 20:
                    print_event("⚠️ Partie trop longue, arrêt forcé")
                    break

            # ============================================
            # RÉCAPITULATIF FINAL
            # ============================================
            print_header("FIN DE LA PARTIE", "🎭")

            result = await session.call_tool("get_game_state", {"game_id": game_id})
            final_state = json.loads(result.content[0].text)

            status = final_state["status"]
            if status == "victoire_village":
                print("\n  🏠 LE VILLAGE A GAGNÉ!")
                print("  Tous les loups-garous ont été éliminés.")
                win = my_faction == "Village"
            else:
                print("\n  🐺 LES LOUPS-GAROUS ONT GAGNÉ!")
                print("  Les loups ont pris le contrôle du village.")
                win = my_faction == "Loups-Garous"

            print(f"\n  Votre rôle était: {my_role} ({my_faction})")
            print(f"  {'🎉 VOUS AVEZ GAGNÉ!' if win else '😢 Vous avez perdu...'}")

            print("\n  📜 Récapitulatif des rôles:")
            print("\n  Morts:")
            for p in final_state.get("dead_players", []):
                print(f"     💀 {p['name']} - {p['role']}")

            print("\n  Survivants:")
            for p in final_state.get("alive_players", []):
                marker = " (vous)" if p.get("is_you") else ""
                print(f"     ✅ {p['name']}{marker}")

            print("\n  Merci d'avoir joué! 🐺\n")


if __name__ == "__main__":
    asyncio.run(play_interactive_game())

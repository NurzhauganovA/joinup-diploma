def active_page(request):
    club_part = request.path.split('/')[1] if len(request.path.split('/')) > 1 else ''
    if club_part == 'panel':
        return {
            "active_page": "club"
        }

    contract_part = request.path.split('/')[1] if len(request.path.split('/')) > 1 else ''
    if contract_part == 'contracts':
        return {
            "active_page": "contract"
        }
    return {
        "active_page": request.path
    }

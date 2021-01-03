
class StatsCard(dict):

    def __init__(self, stat, **kwargs):

        super(StatsCard, self).__init__()
        default_dict = {"big_icon": "",
                        "title": "",
                        "stat": stat,
                        "card_type": True,
                        "footer_type": "",
                        "footer_icon":"",
                        "footer_href": "",
                        "footer_text":""}

        data = {**default_dict, **kwargs}
        for key in data:
            self[key] = data[key]

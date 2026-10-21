def get_wind_direction_text(degree):
    if degree is None:
        return "نامشخص"
    if 337.5 <= degree or degree < 22.5:
        return "شمال"
    elif 22.5 <= degree < 67.5:
        return "شمال‌شرق"
    elif 67.5 <= degree < 112.5:
        return "شرق"
    elif 112.5 <= degree < 157.5:
        return "جنوب‌شرق"
    elif 157.5 <= degree < 202.5:
        return "جنوب"
    elif 202.5 <= degree < 247.5:
        return "جنوب‌غرب"
    elif 247.5 <= degree < 292.5:
        return "غرب"
    elif 292.5 <= degree < 337.5:
        return "شمال‌غرب"
    return "نامشخص"

def analyze_wind_source(point_name, degree):
    direction = get_wind_direction_text(degree)
    
    if point_name in ["زابل (سیستان)", "زاهدان"]:
        if direction in ["شمال", "شمال‌غرب", "غرب"]:
            return f"از سمت {direction} (منشأ احتمالی: کویرهای مرکزی ایران)"
        elif direction in ["جنوب", "جنوب‌شرق", "شرق"]:
            return f"از سمت {direction} (منشأ احتمالی: بیابان‌های افغانستان و پاکستان)"
    
    elif point_name in ["اهواز", "بوشهر", "خلیج فارس"]:
        if direction in ["شمال", "شمال‌غرب"]:
            return f"از سمت {direction} (منشأ احتمالی: عراق و سوریه)"
        elif direction in ["جنوب", "جنوب‌شرق"]:
            return f"از سمت {direction} (منشأ احتمالی: بیابان‌های عربستان)"
    
    elif point_name == "تهران":
        if direction in ["غرب", "جنوب‌غرب"]:
            return f"از سمت {direction} (منشأ احتمالی: کویر مرکزی و دشت‌های غربی)"
            
    return f"از سمت {direction}"